"""Enrichment tasks for LinkedIn scraping and context extraction.

These are I/O-intensive tasks that query LinkedIn, Twitter, and other sources
to enrich interaction data with social context.
Routed to the 'enrichment' worker queue using Gevent.
"""

import logging
import json
import time
from datetime import datetime, timedelta
from celery import Task
from ..celery_app import app
from ..services import linkedin_scraper
from ..config import settings
from ..db import SessionLocal, redis_cache

logger = logging.getLogger(__name__)

# Circuit breaker state: {ip_hash: {"blocked_until": timestamp, "reason": "CAPTCHA"}}
CIRCUIT_BREAKER_STATE = {}


class EnrichmentTask(Task):
    """Base task class for enrichment with rate limiting."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 1800  # 30 minutes max
    retry_jitter = True


def check_circuit_breaker(ip_hash: str) -> bool:
    """Check if scraping is blocked for this IP.
    
    Returns:
        True if circuit is OPEN (blocked), False if CLOSED (allowed)
    """
    state = CIRCUIT_BREAKER_STATE.get(ip_hash)
    if not state:
        return False
    
    if datetime.now() < state["blocked_until"]:
        logger.warning(f"Circuit breaker OPEN for {ip_hash}: {state['reason']}")
        return True
    
    # Reset circuit
    del CIRCUIT_BREAKER_STATE[ip_hash]
    logger.info(f"Circuit breaker RESET for {ip_hash}")
    return False


def trip_circuit_breaker(ip_hash: str, reason: str = "CAPTCHA", duration_hours: int = 1):
    """Trip the circuit breaker to prevent IP blacklisting.
    
    Args:
        ip_hash: IP hash or user agent hash
        reason: Reason for blocking (CAPTCHA, RateLimit, etc.)
        duration_hours: How long to block (default 1 hour)
    """
    blocked_until = datetime.now() + timedelta(hours=duration_hours)
    CIRCUIT_BREAKER_STATE[ip_hash] = {
        "blocked_until": blocked_until,
        "reason": reason,
    }
    logger.warning(f"Circuit breaker TRIPPED for {ip_hash}: {reason} (blocked until {blocked_until})")


@app.task(bind=True, base=EnrichmentTask, name="src.tasks.enrichment_tasks.extract_name_context")
def extract_name_context(self, transcription_result: dict):
    """Extract searchable name/context from transcript using Gemini.
    
    Uses LLM to identify mentions of people and create search queries.
    
    Args:
        transcription_result: Dict with extracted_interests
        
    Returns:
        Dict with persons list and search queries
    """
    job_id = transcription_result.get("job_id")
    extracted_interests = transcription_result.get("extracted_interests", "")
    
    logger.info(f"[job_id={job_id}] Extracting names/context from transcript")
    self.update_state(state="NAME_EXTRACTION", meta={"progress": "Finding contact names..."})
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        
        prompt = f"""From this conversation transcript, identify any person names mentioned.
For each person found, create a search query that includes:
- Full name (if available)
- Location/region (if mentioned)
- Job/title (if mentioned)  
- Company (if mentioned)

Transcript: {extracted_interests[:2000]}

Return JSON: {{"persons": [{{"name": "...", "search_query": "...", "confidence": 0.8}}]}}

Return ONLY valid JSON."""
        
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.5,
                max_output_tokens=500,
            ),
        )
        
        persons = json.loads(response.text)
        logger.info(f"[job_id={job_id}] Extracted {len(persons.get('persons', []))} names")
        
        return {
            **transcription_result,
            "persons": persons.get("persons", []),
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Name extraction failed: {e}")
        self.update_state(
            state="NAME_EXTRACTION_FAILED",
            meta={"error": str(e)}
        )
        # Don't raise - enrichment is optional
        return {
            **transcription_result,
            "persons": [],
        }


@app.task(bind=True, base=EnrichmentTask, name="src.tasks.enrichment_tasks.scrape_linkedin")
def scrape_linkedin(self, enrichment_result: dict):
    """Scrape LinkedIn profiles for extracted names with circuit breaker.
    
    Args:
        enrichment_result: Dict with persons list from name extraction
        
    Returns:
        Dict with scraped social context
    """
    job_id = enrichment_result.get("job_id")
    persons = enrichment_result.get("persons", [])
    
    logger.info(f"[job_id={job_id}] Starting LinkedIn scraping for {len(persons)} profiles")
    self.update_state(state="SCRAPING", meta={"progress": f"Scraping {len(persons)} profiles..."})
    
    try:
        # Check circuit breaker
        IP_HASH = "default_session"  # In production, use actual IP/proxy hash
        if check_circuit_breaker(IP_HASH):
            logger.warning(f"[job_id={job_id}] LinkedIn scraping blocked by circuit breaker")
            return {
                **enrichment_result,
                "scraped_profiles": [],
                "scraping_blocked": True,
            }
        
        scraped_profiles = []
        for person in persons:
            try:
                search_query = person.get("search_query", "")
                if not search_query:
                    continue
                
                # Attempt LinkedIn scrape
                logger.info(f"[job_id={job_id}] Scraping: {search_query}")
                profile_data = linkedin_scraper.scrape_profile(search_query)
                
                if profile_data:
                    scraped_profiles.append({
                        "person": person["name"],
                        "profile": profile_data,
                        "source": "linkedin",
                    })
                    logger.info(f"[job_id={job_id}] Successfully scraped: {person['name']}")
                
            except Exception as e:
                # Check for CAPTCHA or rate limit
                if "CAPTCHA" in str(e) or "429" in str(e):
                    trip_circuit_breaker(IP_HASH, reason="CAPTCHA_OR_RATELIMIT", duration_hours=1)
                    logger.warning(f"[job_id={job_id}] Circuit breaker tripped: {e}")
                    break  # Stop scraping
                else:
                    logger.warning(f"[job_id={job_id}] Profile scrape failed for {person['name']}: {e}")
                    continue
        
        logger.info(f"[job_id={job_id}] Scraping complete: {len(scraped_profiles)} profiles")
        
        return {
            **enrichment_result,
            "scraped_profiles": scraped_profiles,
            "scraping_blocked": False,
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Scraping task failed: {e}")
        self.update_state(
            state="SCRAPING_FAILED",
            meta={"error": str(e)}
        )
        # Return gracefully - scraping is enrichment, not critical
        return {
            **enrichment_result,
            "scraped_profiles": [],
            "scraping_error": str(e),
        }


@app.task(bind=True, name="src.tasks.enrichment_tasks.scrape_twitter")
def scrape_twitter(self, enrichment_result: dict):
    """Fallback scraper: Get public Twitter/X profiles if LinkedIn is blocked.
    
    Args:
        enrichment_result: Dict with persons list
        
    Returns:
        Dict with Twitter profiles
    """
    job_id = enrichment_result.get("job_id")
    persons = enrichment_result.get("persons", [])
    
    # Check if LinkedIn was blocked
    if not enrichment_result.get("scraping_blocked", False):
        return enrichment_result
    
    logger.info(f"[job_id={job_id}] Fallback: Scraping Twitter for {len(persons)} profiles")
    self.update_state(state="TWITTER_FALLBACK", meta={"progress": "Checking Twitter profiles..."})
    
    try:
        twitter_profiles = []
        # TODO: Implement Twitter/X scraping with nitter.net or similar proxy
        # For now, skip as Twitter requires auth
        
        return {
            **enrichment_result,
            "twitter_profiles": twitter_profiles,
        }
        
    except Exception as e:
        logger.warning(f"[job_id={job_id}] Twitter fallback failed: {e}")
        return enrichment_result
