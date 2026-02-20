"""Synthesis and PII scrubbing tasks.

These tasks create final insights and ensure data privacy compliance.
"""

import logging
import re
import json
from celery import Task
from ..celery_app import app
from ..config import settings
from ..db import SessionLocal
from ..models import InteractionMetric

logger = logging.getLogger(__name__)


class SynthesisTask(Task):
    """Base task for synthesis operations."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 2}
    retry_backoff = True


@app.task(bind=True, base=SynthesisTask, name="src.tasks.synthesis_tasks.recursive_insight")
def recursive_insight(self, enrichment_result: dict):
    """Generate final insight by comparing persona against transcript + scraped data.
    
    The Recursive Synthesis uses three data sources:
    1. User's persona vector
    2. Extracted interests from transcript
    3. Scraped social context (LinkedIn, Twitter)
    
    Creates a polished "Insight" that represents the intersection of all three.
    
    Args:
        enrichment_result: Dict with extracted_interests and scraped_profiles
        
    Returns:
        Dict with final_insight and metadata
    """
    job_id = enrichment_result.get("job_id")
    extracted_interests = enrichment_result.get("extracted_interests", "")
    scraped_profiles = enrichment_result.get("scraped_profiles", [])
    
    logger.info(f"[job_id={job_id}] Generating recursive insight")
    self.update_state(state="SYNTHESIS", meta={"progress": "Creating personalized insight..."})
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        
        # Build context from scraped data
        context_sections = []
        for profile in scraped_profiles:
            person_name = profile.get("person", "Unknown")
            source = profile.get("source", "unknown")
            context_sections.append(f"Found context from {source}: {person_name}")
        
        context_text = "\n".join(context_sections) if context_sections else "No social context found."
        
        prompt = f"""Based on this conversation and social context, generate a brief, actionable insight.

Conversation Interests: {extracted_interests[:1000]}

Social Context:
{context_text}

Create a JSON response with:
1. "summary": One sentence summary of the key insight
2. "overlap_points": List of 2-3 shared interests found
3. "action_items": List of 2-3 suggested follow-ups (e.g., "Explore their React.js projects", "Connect on GitHub")

Return ONLY valid JSON."""
        
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
            ),
        )
        
        insight = json.loads(response.text)
        logger.info(f"[job_id={job_id}] Insight generated: {insight.get('summary', '')}")
        
        return {
            **enrichment_result,
            "final_insight": insight,
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Synthesis failed: {e}")
        self.update_state(
            state="SYNTHESIS_FAILED",
            meta={"error": str(e)}
        )
        raise


@app.task(bind=True, name="src.tasks.synthesis_tasks.draft_warm_outreach")
def draft_warm_outreach(self, synthesis_result: dict):
    """Draft a personalized warm outreach message using overlap points.
    
    Uses the final insight to create a 2-3 sentence personalized message
    that can be sent via LinkedIn, email, or messaging.
    
    Args:
        synthesis_result: Dict with final_insight
        
    Returns:
        Dict with draft_message
    """
    job_id = synthesis_result.get("job_id")
    final_insight = synthesis_result.get("final_insight", {})
    person_name = synthesis_result.get("persons", [{}])[0].get("name", "there")
    
    logger.info(f"[job_id={job_id}] Drafting warm outreach message")
    self.update_state(state="OUTREACH", meta={"progress": "Drafting personalized message..."})
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        
        overlap_points = final_insight.get("overlap_points", [])
        
        prompt = f"""Draft a warm, 2-3 sentence outreach message for a professional connection.

Person: {person_name}
Overlap Points: {', '.join(overlap_points)}

Guidelines:
- Start with a specific observation from your conversation
- Reference one overlap point
- Suggest one concrete next step
- Keep it genuine and conversational (not salesy)

Return a short message (max 150 words) that would work for LinkedIn or email."""
        
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=300,
            ),
        )
        
        message = response.text.strip()
        logger.info(f"[job_id={job_id}] Warm outreach drafted ({len(message)} chars)")
        
        return {
            **synthesis_result,
            "draft_message": message,
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Message draft failed: {e}")
        # Non-critical task, return gracefully
        return {
            **synthesis_result,
            "draft_message": None,
        }


# PII Scrubbing patterns
PII_PATTERNS = {
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\+?\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
}


@app.task(bind=True, name="src.tasks.synthesis_tasks.scrub_pii")
def scrub_pii(self, synthesis_result: dict) -> dict:
    """Remove personally identifiable information from transcript before storage.
    
    Detects and masks:
    - Phone numbers
    - Email addresses
    - Social Security numbers
    - Credit card numbers
    
    Args:
        synthesis_result: Dict with extracted_interests (transcript)
        
    Returns:
        Dict with cleaned_transcript and pii_detected
    """
    job_id = synthesis_result.get("job_id")
    transcript = synthesis_result.get("extracted_interests", "")
    
    logger.info(f"[job_id={job_id}] Scrubbing PII from transcript")
    self.update_state(state="PII_SCRUBBING", meta={"progress": "Removing sensitive data..."})
    
    cleaned = transcript
    pii_detected = {}
    
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, transcript)
        if matches:
            pii_detected[pii_type] = len(matches)
            # Replace with masked version
            cleaned = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", cleaned)
            logger.warning(f"[job_id={job_id}] Found and scrubbed {len(matches)} {pii_type}(s)")
    
    logger.info(f"[job_id={job_id}] PII scrubbing complete. Detections: {pii_detected}")
    
    return {
        **synthesis_result,
        "cleaned_transcript": cleaned,
        "pii_detected": pii_detected,
    }


@app.task(bind=True, name="src.tasks.synthesis_tasks.store_metrics")
def store_metrics(self, final_result: dict):
    """Store interaction metrics and final insight to database.
    
    Args:
        final_result: Complete result dict from workflow
        
    Returns:
        Database IDs created
    """
    job_id = final_result.get("job_id")
    user_id = final_result.get("user_id")
    conversation_id = final_result.get("conversation_id")
    embedding = final_result.get("embedding", [])
    final_insight = final_result.get("final_insight", {})
    draft_message = final_result.get("draft_message", "")
    
    logger.info(f"[job_id={job_id}] Storing metrics to database")
    self.update_state(state="STORING", meta={"progress": "Saving to database..."})
    
    try:
        db = SessionLocal()
        
        # Store interaction metrics
        metric = InteractionMetric(
            user_id=user_id,
            interaction_id=conversation_id,
            mode="live",  # Can be parameterized
            top_synapse_similarity=0.0,  # Will be set by overlap engine
            avg_similarity=0.0,
            extraction_accuracy=0.0,
            processing_time_ms=0,
            user_approved=0,
            user_rejected=0,
        )
        db.add(metric)
        db.commit()
        metric_id = metric.id
        db.close()
        
        logger.info(f"[job_id={job_id}] Metrics stored (metric_id={metric_id})")
        
        return {
            **final_result,
            "metric_id": metric_id,
            "status": "SUCCESS",
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Failed to store metrics: {e}")
        raise

@app.task(bind=True, name="src.tasks.synthesis_tasks.triple_vector_synthesis")
def triple_vector_synthesis(self, synthesis_result: dict):
    """Combine three data vectors into unified profile embedding.
    
    Phase 2b enhancement: Fuse multiple data sources into single embedding
    
    Vector 1 (40%): Transcript embedding (user's interests from speech)
    Vector 2 (40%): Professional data embedding (LinkedIn headline, skills)
    Vector 3 (20%): Personality data embedding (Twitter topics, Instagram aesthetic, TikTok niche)
    
    Fusion approach:
    - Weighted combination with configurable weights
    - Final unified embedding used for vector similarity matching
    - Can fall back to individual vectors if some sources fail (graceful degradation)
    
    Args:
        synthesis_result: Dict with transcript_embedding and scraped source data
        
    Returns:
        Dict with unified_profile_embedding
    """
    job_id = synthesis_result.get("job_id")
    transcript_embedding = synthesis_result.get("embedding", [])
    scraped_data = synthesis_result.get("scraped_profiles", [])
    
    logger.info(f"[job_id={job_id}] Starting triple-vector synthesis")
    self.update_state(state="TRIPLE_VECTOR", meta={"progress": "Fusing data vectors..."})
    
    try:
        import google.generativeai as genai
        import numpy as np
        genai.configure(api_key=settings.gemini_api_key)
        
        # Vector 1: Transcript embedding (already have)
        if not transcript_embedding:
            logger.warning(f"[job_id={job_id}] No transcript embedding available")
            vector_1 = np.zeros(1536)
        else:
            vector_1 = np.array(transcript_embedding[:1536])
        
        # Vector 2: Professional data embedding (LinkedIn, GitHub)
        professional_text = ""
        for profile in scraped_data:
            if profile.get("source") in ["linkedin", "github"]:
                professional_text += f" {profile.get('profile_text', '')}"
        
        if professional_text.strip():
            # Get embedding for professional data
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.embed_content(professional_text[:1000])
            vector_2 = np.array(response['embedding'][:1536])
            # Pad if necessary
            if len(vector_2) < 1536:
                vector_2 = np.pad(vector_2, (0, 1536 - len(vector_2)))
        else:
            logger.debug(f"[job_id={job_id}] No professional data for embedding")
            vector_2 = np.zeros(1536)
        
        # Vector 3: Personality data embedding (Twitter, Instagram, TikTok)
        personality_text = ""
        for profile in scraped_data:
            if profile.get("source") in ["twitter", "instagram", "tiktok"]:
                personality_text += f" {profile.get('profile_text', '')}"
        
        if personality_text.strip():
            # Get embedding for personality data
            response = model.embed_content(personality_text[:1000])
            vector_3 = np.array(response['embedding'][:1536])
            # Pad if necessary
            if len(vector_3) < 1536:
                vector_3 = np.pad(vector_3, (0, 1536 - len(vector_3)))
        else:
            logger.debug(f"[job_id={job_id}] No personality data for embedding")
            vector_3 = np.zeros(1536)
        
        # Weighted fusion (configurable)
        weights = {
            "transcript": 0.4,
            "professional": 0.4,
            "personality": 0.2,
        }
        
        unified_embedding = (
            weights["transcript"] * vector_1 +
            weights["professional"] * vector_2 +
            weights["personality"] * vector_3
        )
        
        # Normalize to unit vector (for cosine similarity)
        norm = np.linalg.norm(unified_embedding)
        if norm > 0:
            unified_embedding = unified_embedding / norm
        
        logger.info(
            f"[job_id={job_id}] Triple-vector synthesis complete. "
            f"Unified embedding shape: {unified_embedding.shape}"
        )
        
        return {
            **synthesis_result,
            "unified_profile_embedding": unified_embedding.tolist(),
            "vector_weights": weights,
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Triple-vector synthesis failed: {e}")
        # Graceful degradation: fall back to transcript embedding
        return {
            **synthesis_result,
            "unified_profile_embedding": synthesis_result.get("embedding", []),
            "vector_weights": {"transcript": 1.0},
            "degraded": True,
        }


@app.task(bind=True, name="src.tasks.synthesis_tasks.calculate_social_quadrant")
def calculate_social_quadrant(self, synthesis_result: dict):
    """Map person across 4D social space.
    
    Phase 2b enhancement: Calculate social quadrant (professional/creative/casual/realtime)
    
    Dimensions:
    - Professional: LinkedIn activity, GitHub presence, career focus
    - Creative: Instagram, TikTok, personal brand, content creation
    - Casual: Twitter frequency, casual topics, meme sharing
    - Real-time: Recent activity freshness, trending topic engagement
    
    Args:
        synthesis_result: Dict with scraped_profiles data
        
    Returns:
        Dict with social_quadrant scores
    """
    job_id = synthesis_result.get("job_id")
    scraped_data = synthesis_result.get("scraped_profiles", [])
    
    logger.info(f"[job_id={job_id}] Calculating social quadrant")
    
    try:
        from ..services.social_quadrant import SocialQuadrantMapper
        
        mapper = SocialQuadrantMapper()
        
        # Build sources_data dict from scraped profiles
        sources_data = {}
        for profile in scraped_data:
            source = profile.get("source", "unknown")
            sources_data[source] = profile.get("profile_data", {})
        
        # Calculate quadrant
        quadrant = mapper.calculate_from_sources(sources_data)
        
        # Get communication strategy
        strategy = mapper.get_communication_strategy(quadrant)
        
        logger.info(f"[job_id={job_id}] Quadrant: {quadrant.to_dict()}")
        
        return {
            **synthesis_result,
            "social_quadrant": quadrant.to_dict(),
            "communication_strategy": strategy,
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Social quadrant calculation failed: {e}")
        # Graceful degradation
        return {
            **synthesis_result,
            "social_quadrant": {
                "professional": 0.5,
                "creative": 0.5,
                "casual": 0.5,
                "realtime": 0.5,
            },
            "degraded": True,
        }


@app.task(bind=True, name="src.tasks.synthesis_tasks.draft_warm_outreach_v2")
def draft_warm_outreach_v2(self, synthesis_result: dict):
    """Draft personalized outreach with social hooks (Phase 2b enhancement).
    
    Extends draft_warm_outreach with "Social Hooks" - references to specific
    social media content found during scraping.
    
    Social hooks examples:
    - "I saw your recent post on X about [topic]"
    - "Your GitHub project [repo] looks interesting"
    - "Love your [aesthetic type] vibe on IG"
    - "Your [niche] content on TikTok resonates"
    
    Args:
        synthesis_result: Dict with final_insight and scraped_profiles
        
    Returns:
        Dict with draft_message (enhanced with social hooks)
    """
    job_id = synthesis_result.get("job_id")
    final_insight = synthesis_result.get("final_insight", {})
    person_name = synthesis_result.get("persons", [{}])[0].get("name", "there")
    scraped_data = synthesis_result.get("scraped_profiles", [])
    
    logger.info(f"[job_id={job_id}] Drafting warm outreach v2 with social hooks")
    self.update_state(state="OUTREACH_V2", meta={"progress": "Adding social hooks..."})
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        
        overlap_points = final_insight.get("overlap_points", [])
        
        # Extract social hooks from scraped data
        social_hooks = []
        for profile in scraped_data:
            source = profile.get("source", "unknown")
            
            if source == "twitter" and profile.get("recent_posts"):
                topic = profile["recent_posts"][0].get("topic", "X")
                social_hooks.append(f"your recent post on X about {topic}")
            elif source == "github" and profile.get("top_repos"):
                repo = profile["top_repos"][0]
                social_hooks.append(f'your GitHub project "{repo}"')
            elif source == "instagram" and profile.get("aesthetic"):
                aesthetic = profile.get("aesthetic", "Instagram aesthetic")
                social_hooks.append(f"your {aesthetic} vibe on IG")
            elif source == "tiktok" and profile.get("niche"):
                niche = profile.get("niche", "TikTok content")
                social_hooks.append(f"your {niche} content on TikTok")
        
        hooks_text = ""
        if social_hooks:
            hooks_text = f"\n\nSpecific observations:\n" + "\n".join(
                f"- I saw {hook}" for hook in social_hooks[:2]
            )
        
        prompt = f"""Draft a warm, 3-4 sentence outreach message for a professional connection.

Person: {person_name}
Overlap Points: {', '.join(overlap_points)}
Social Context:{hooks_text}

Guidelines:
- Start with a specific observation from your conversation
- Include 1-2 of the social observations (e.g., "I saw your recent post about...")
- Reference one overlap point
- Suggest one concrete next step (coffee chat, review their work, connect on a platform)
- Keep it genuine and conversational (not salesy)
- Maximum 200 words

Return ONLY the message (no preamble)."""
        
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=400,
            ),
        )
        
        message = response.text.strip()
        logger.info(f"[job_id={job_id}] Warm outreach v2 drafted ({len(message)} chars, {len(social_hooks)} hooks)")
        
        return {
            **synthesis_result,
            "draft_message": message,
            "social_hooks_used": social_hooks[:2],
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Message draft v2 failed: {e}")
        # Fall back to v1 without social hooks
        return draft_warm_outreach(synthesis_result)