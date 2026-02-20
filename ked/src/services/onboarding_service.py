import logging
import json
import google.generativeai as genai
from sqlalchemy.orm import Session

from ..models import UserPersona, InterestNode
from ..config import settings
from . import deepgram_integration, linkedin_scraper

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)


def ingest_voice_pitch(user_id: int, audio_file_path: str, db: Session) -> list[dict]:
    """Ingest a 60-second voice pitch, transcribe it, and generate persona nodes.

    Returns list of persona nodes with labels and weights.
    """
    # Transcribe the audio
    transcription_result = deepgram_integration.transcribe_audio(audio_file_path, diarize=False)

    # Extract transcript
    try:
        transcript = transcription_result["results"]["channels"][0]["alternatives"][0]["transcript"]
    except (KeyError, IndexError) as e:
        logger.error(f"[user_id={user_id}] Failed to extract transcript: {e}")
        return []

    logger.info(f"[user_id={user_id}] Transcribed voice pitch: {transcript[:100]}...")

    # Generate persona nodes from transcript
    nodes = _synthesize_personas(transcript)

    # Store in database
    for node in nodes:
        persona = UserPersona(
            user_id=user_id,
            label=node["label"],
            weight=node.get("weight", 1),
        )
        db.add(persona)

    db.commit()
    logger.info(f"[user_id={user_id}] Created {len(nodes)} persona nodes from voice pitch")
    return nodes


def ingest_linkedin_profile(user_id: int, profile_url: str, db: Session) -> list[dict]:
    """Scrape a LinkedIn profile and generate persona nodes.

    Returns list of persona nodes with labels and weights.
    """
    
    # Scrape the profile
    profile_data = linkedin_scraper.scrape_profile(profile_url)
    logger.info(f"[user_id={user_id}] Scraped LinkedIn profile from {profile_url}")

    # Extract key information (bio, headline, experience)
    text_for_synthesis = _extract_profile_text(profile_data)

    # Generate persona nodes
    nodes = _synthesize_personas(text_for_synthesis)

    # Store in database
    for node in nodes:
        persona = UserPersona(
            user_id=user_id,
            label=node["label"],
            weight=node.get("weight", 1),
        )
        db.add(persona)

    db.commit()
    logger.info(f"[user_id={user_id}] Created {len(nodes)} persona nodes from LinkedIn profile")
    return nodes


def _synthesize_personas(text: str) -> list[dict]:
    """Use Google Gemini to extract key interests/personas from text.

    Returns a list of dicts with 'label' and 'weight'.
    """
    prompt = (
        "You are an expert at identifying professional personas and interests from text. "
        "Extract and list 5-10 key interests, skills, or personas from the following text. "
        "Return a JSON array of objects with 'label' (string) and 'weight' (integer 1-10).\n"
        "Focus on unique, specific identifiers (e.g., 'React Developer', 'AI/ML Enthusiast', 'Quantum Physics').\n\n"
        f"Text:\n{text}\n\n"
        "Return ONLY valid JSON, no markdown or extra text."
    )

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
            ),
        )
        output_text = response.text.strip()
        
        # Parse JSON response
        nodes = json.loads(output_text)
        
        # Validate structure
        for node in nodes:
            if "label" not in node:
                node["label"] = str(node)
            if "weight" not in node:
                node["weight"] = 5
        return nodes
    except Exception as e:
        logger.error(f"Error synthesizing personas with Gemini: {e}")
        return []


def _extract_profile_text(profile_data: dict) -> str:
    """Extract relevant text from scraped LinkedIn profile data."""
    # For now, return raw HTML; in production, parse specific fields
    return profile_data.get("raw_html", "")[:2000]  # Truncate for LLM
