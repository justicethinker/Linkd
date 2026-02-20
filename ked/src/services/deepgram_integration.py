import logging
import re
import google.generativeai as genai
from deepgram import Deepgram
from ..config import settings

logger = logging.getLogger(__name__)

dg_client = Deepgram(settings.deepgram_api_key)
genai.configure(api_key=settings.gemini_api_key)

# Filler words to remove from extracted interests
FILLER_WORDS = {
    "um", "uh", "ah", "er", "hmm", "like", "you know", "basically",
    "actually", "literally", "just", "kind of", "sort of", "yeah", "yep",
    "okay", "okay", "alright", "right", "uh-huh", "mm-hmm"
}


def clean_filler_words(text: str) -> str:
    """Remove filler words and normalize whitespace.
    
    Args:
        text: Raw text with potential filler words
        
    Returns:
        Cleaned text with filler words removed and normalized spacing
    """
    if not text:
        return ""
    
    # Convert to lowercase for matching, then clean
    words = text.split()
    cleaned = []
    
    for word in words:
        word_lower = word.lower().strip(".,!?;:")
        if word_lower not in FILLER_WORDS and len(word_lower) > 0:
            cleaned.append(word)
    
    # Normalize whitespace
    result = " ".join(cleaned)
    result = re.sub(r"\s+", " ", result).strip()
    
    logger.debug(f"Cleaned text: '{text[:50]}...' -> '{result[:50]}...'")
    return result


def transcribe_audio(file_path: str, diarize: bool = False) -> dict:
    """Send an audio file to Deepgram and return the transcription result.

    Args:
        file_path: local path to the audio file
        diarize: whether to run diarization (live mode)
        
    Returns:
        Deepgram API response dict
        
    Note:
        Uses nova-2 model with smart_format for enhanced accuracy.
        smart_format=true: Cleans up text (casing, punctuation, entity normalization)
        model=nova-2: State-of-the-art for fast, accurate conversational speech
    """
    try:
        with open(file_path, "rb") as f:
            source = {"buffer": f, "mimetype": "audio/wav"}
            response = dg_client.transcription.pre_recorded(
                source,
                {
                    "model": "nova-2",
                    "diarize": diarize,
                    "smart_format": True,
                    "punctuate": True,
                    "entities": True,
                },
            )
        logger.info(f"Deepgram transcription completed (diarize={diarize}, model=nova-2)")
        return response
    except Exception as e:
        logger.error(f"Deepgram transcription failed: {e}")
        raise


def extract_other_speaker_interests(transcript_data: dict) -> str:
    """Extract interests from the 'Other' speaker in a diarized transcript (Live mode).

    The system must distinguish between Your Voice (Speaker 0) and the Contact's Voice (Speaker 1).
    We don't want to match your own interests against yourself; we want to find the delta 
    between you and the other person.
    
    Logic Flow:
    1. Segregate: Separate transcript into user_utterances (Speaker 0) and contact_utterances (Speaker 1)
    2. Clean: Remove filler words ("um", "ah") and non-substantive phrases
    3. Embed: Contact utterances are converted to embedding in interactions router
    
    Fault Tolerance: If diarization is messy (high noise at a club), falls back to treating 
    entire transcript as a Bag of Words to find interests.

    Args:
        transcript_data: Deepgram API response dict with diarized paragraphs
        
    Returns:
        Cleaned contact speaker text (or fallback bag of words if diarization fails)
    """
    # Initialize buckets for speaker segregation
    user_utterances = []      # Speaker ID 0 (self)
    contact_utterances = []   # Speaker ID 1+ (other)
    
    # Parse diarized output
    try:
        paragraphs = transcript_data["results"]["channels"][0]["alternatives"][0]["paragraphs"]["paragraphs"]
    except (KeyError, IndexError, TypeError):
        logger.warning("Could not extract paragraphs from diarized transcript - falling back to bag of words")
        return _fallback_bag_of_words(transcript_data)
    
    # Segregate speakers
    if not paragraphs:
        logger.warning("Paragraphs list is empty - falling back to bag of words")
        return _fallback_bag_of_words(transcript_data)
    
    for para in paragraphs:
        if "speaker" not in para:
            # No speaker info; skip or add to contact (safer fallback)
            logger.debug("Paragraph has no speaker info; skipping")
            continue
            
        speaker_id = para.get("speaker")
        paragraph_text = []
        
        for sentence in para.get("sentences", []):
            paragraph_text.append(sentence.get("text", ""))
        
        joined_text = " ".join(paragraph_text)
        
        if speaker_id == 0:
            user_utterances.append(joined_text)
        else:
            # Speaker 1+ is the contact
            contact_utterances.append(joined_text)
    
    # Check if we got contact utterances
    if not contact_utterances:
        logger.warning("No contact speaker utterances found - falling back to bag of words")
        return _fallback_bag_of_words(transcript_data)
    
    # Clean contact utterances
    contact_text = " ".join(contact_utterances)
    cleaned_contact_text = clean_filler_words(contact_text)
    
    logger.info(
        f"Speaker segregation: User={len(user_utterances)} utterances, "
        f"Contact={len(contact_utterances)} utterances (cleaned: {len(cleaned_contact_text)} chars)"
    )
    return cleaned_contact_text


def _fallback_bag_of_words(transcript_data: dict) -> str:
    """Fallback extraction: treat entire transcript as Bag of Words when diarization fails.
    
    Used when diarization is messy (e.g., high noise at a club). Extracts all entities 
    and concatenates into a searchable interest string.
    
    Args:
        transcript_data: Deepgram API response dict
        
    Returns:
        Concatenated entity string from entire transcript
    """
    logger.info("Falling back to Bag of Words extraction (diarization unreliable)")
    entities = extract_entities_from_transcript(transcript_data)
    
    if entities:
        result = " ".join(entities)
        logger.info(f"Bag of Words extracted {len(entities)} entities: {result[:100]}...")
        return result
    
    # Last resort: extract raw transcript
    try:
        alternatives = transcript_data["results"]["channels"][0]["alternatives"]
        if alternatives:
            raw_text = alternatives[0].get("transcript", "")
            cleaned = clean_filler_words(raw_text)
            logger.info(f"Fallback bag of words from raw transcript: {cleaned[:100]}...")
            return cleaned
    except (KeyError, IndexError, TypeError):
        pass
    
    logger.warning("Bag of Words fallback also failed - returning empty string")
    return ""


def extract_entities_from_transcript(transcript_data: dict) -> list[str]:
    """Extract named entities and interests from the full transcript (Recap mode).

    In recap mode (diarize=false), describes a conversation.
    This function pulls entities like person names, topics, interests.
    
    Extracted entities are cleaned of filler words and normalized.

    Args:
        transcript_data: Deepgram API response dict
        
    Returns:
        List of cleaned entity strings (SKILL, TOPIC, ORGANIZATION, PERSON types)
    """
    try:
        alternatives = transcript_data["results"]["channels"][0]["alternatives"]
        entities = []
        
        for alt in alternatives:
            if "entities" in alt:
                for entity in alt["entities"]:
                    entity_type = entity.get("type", "")
                    entity_text = entity.get("value", "")
                    
                    # Interest-related entity types
                    if entity_type in ("SKILL", "TOPIC", "ORGANIZATION", "PERSON"):
                        # Clean the entity text
                        cleaned_entity = clean_filler_words(entity_text)
                        if cleaned_entity:
                            entities.append(cleaned_entity)
        
        logger.info(f"Extracted {len(entities)} cleaned entities from transcript")
        return entities
    except (KeyError, IndexError, TypeError) as e:
        logger.warning(f"Could not extract entities from transcript: {e}")
        return []


def process_interaction_audio(file_path: str, mode: str = "recap") -> str:
    """Process audio from an interaction and return the extracted interests.

    Args:
        file_path: path to the audio file
        mode: 'live' (diarize=true) or 'recap' (diarize=false)

    Returns:
        Extracted interests as a string.
    """
    diarize = mode == "live"
    transcript_data = transcribe_audio(file_path, diarize=diarize)

    if mode == "live":
        return extract_other_speaker_interests(transcript_data)
    else:
        entities = extract_entities_from_transcript(transcript_data)
        return " ".join(entities)


def get_interaction_embedding(text: str) -> list[float]:
    """Convert extracted interests text to a 1536-dimensional embedding.
    
    Uses Google Gemini's embedding API (768-dimension, padded to 1536 for DB schema compatibility).
    These embeddings are compared against persona embeddings using cosine similarity (threshold 0.70).
    
    Args:
        text: Extracted interests text from Deepgram processing
        
    Returns:
        List of 1536 floats representing semantic vector (padded). Returns zero vector if embedding fails.
        
    Note:
        This is used in the Semantic Overlap Engine (Step 3: Embed).
        Gemini native 768-dim padded to 1536 for database schema compatibility.
    """
    if not text or not text.strip():
        logger.warning("Empty text provided to get_interaction_embedding; returning zero vector")
        return [0.0] * 1536
    
    try:
        response = genai.embed_content(
            model="models/embedding-001",
            content=text,
        )
        embedding = response["embedding"]
        # Pad from 768 to 1536 dimensions for database schema compatibility
        padded = embedding + [0.0] * (1536 - len(embedding))
        logger.info(f"Created embedding for interaction text ({len(text)} chars): {text[:50]}...")
        return padded
    except Exception as e:
        logger.error(f"Failed to create embedding for interaction: {e}")
        # Return zero vector as fallback
        return [0.0] * 1536
