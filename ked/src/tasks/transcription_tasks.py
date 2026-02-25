"""Transcription tasks using Deepgram and Celery.

These are CPU-intensive tasks that process audio and extract interests.
Routed to the 'transcription' worker queue.
"""

import logging
import tempfile
import os
from celery import Task
from ..celery_app import app
from ..services import deepgram_integration
from ..db import SessionLocal
from ..models import Conversation, InteractionMetric
from ..supabase_client import SupabaseManager

logger = logging.getLogger(__name__)


class TranscriptionTask(Task):
    """Base task class with shared error handling."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 5}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max
    retry_jitter = True


@app.task(bind=True, base=TranscriptionTask, name="src.tasks.transcription_tasks.transcribe_audio_bytes")
def transcribe_audio_bytes(self, user_id: int, job_id: str, audio_bytes: bytes, mode: str = "recap"):
    """Transcribe audio given raw bytes. Writes to a temp file on the worker.

    This allows the ingest controller to dispatch transcription immediately
    without waiting for storage upload to complete.
    """
    logger.info(f"[job_id={job_id}] Starting byte-based transcription (mode={mode})")
    self.update_state(state="TRANSCRIPTION", meta={"progress": "Transcribing audio with Deepgram (bytes)..."})

    tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".opus")
        tmp.write(audio_bytes)
        tmp.flush()
        tmp.close()

        diarize = mode == "live"
        transcript_data = deepgram_integration.transcribe_audio(tmp.name, diarize=diarize)

        if mode == "live":
            extracted_interests = deepgram_integration.extract_other_speaker_interests(transcript_data)
        else:
            entities = deepgram_integration.extract_entities_from_transcript(transcript_data)
            extracted_interests = " ".join(entities)

        logger.info(f"[job_id={job_id}] Byte transcription complete: {extracted_interests[:100]}...")

        # Update recordings row in Supabase with transcript JSON and mark completed
        try:
            client = SupabaseManager.get_client()
            client.table("recordings").update({"transcript_json": transcript_data, "status": "completed"}).eq("job_id", job_id).eq("user_id", user_id).execute()
            logger.info(f"[job_id={job_id}] Updated recordings row with transcript_json")
        except Exception as e:
            logger.warning(f"[job_id={job_id}] Failed to update recordings row with transcript: {e}")

        return {
            "user_id": user_id,
            "job_id": job_id,
            "extracted_interests": extracted_interests,
            "mode": mode,
        }

    except Exception as e:
        logger.error(f"[job_id={job_id}] Byte transcription failed: {e}")
        self.update_state(state="TRANSCRIPTION_FAILED", meta={"error": str(e)})
        raise

    finally:
        try:
            if tmp and tmp.name and tmp.name.startswith(tempfile.gettempdir()):
                os.unlink(tmp.name)
        except Exception:
            pass


@app.task(bind=True, base=TranscriptionTask, name="src.tasks.transcription_tasks.transcribe_audio")
def transcribe_audio(self, user_id: int, job_id: str, audio_file_path: str, mode: str = "recap"):
    """Transcribe audio using Deepgram with automatic retry on failure.
    
    Args:
        user_id: User ID
        job_id: Job tracking ID
        audio_file_path: Path to audio file
        mode: 'live' (diarized) or 'recap' (entity extraction)
        
    Returns:
        Dict with extracted_interests and metadata
    """
    logger.info(f"[job_id={job_id}] Starting transcription (mode={mode})")
    self.update_state(state="TRANSCRIPTION", meta={"progress": "Transcribing audio with Deepgram..."})
    
    try:
        # Deepgram transcription with Nova-2
        diarize = mode == "live"
        transcript_data = deepgram_integration.transcribe_audio(audio_file_path, diarize=diarize)
        
        # Extract interests based on mode
        if mode == "live":
            extracted_interests = deepgram_integration.extract_other_speaker_interests(transcript_data)
        else:
            entities = deepgram_integration.extract_entities_from_transcript(transcript_data)
            extracted_interests = " ".join(entities)

        logger.info(f"[job_id={job_id}] Transcription complete: {extracted_interests[:100]}...")

        # Update recordings row in Supabase with transcript JSON and mark completed
        try:
            client = SupabaseManager.get_client()
            client.table("recordings").update({"transcript_json": transcript_data, "status": "completed"}).eq("job_id", job_id).eq("user_id", user_id).execute()
            logger.info(f"[job_id={job_id}] Updated recordings row with transcript_json")
        except Exception as e:
            logger.warning(f"[job_id={job_id}] Failed to update recordings row with transcript: {e}")

        return {
            "user_id": user_id,
            "job_id": job_id,
            "extracted_interests": extracted_interests,
            "mode": mode,
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Transcription failed: {e}")
        self.update_state(
            state="TRANSCRIPTION_FAILED",
            meta={"error": str(e)}
        )
        raise


@app.task(bind=True, base=TranscriptionTask, name="src.tasks.transcription_tasks.embed_interests")
def embed_interests(self, transcription_result: dict):
    """Create embedding vector from extracted interests.
    
    Receives output from transcribe_audio task.
    
    Args:
        transcription_result: Dict from transcribe_audio with extracted_interests
        
    Returns:
        Dict with embedding vector and metadata
    """
    job_id = transcription_result.get("job_id")
    extracted_interests = transcription_result.get("extracted_interests", "")
    
    logger.info(f"[job_id={job_id}] Creating embedding from interests")
    self.update_state(state="EMBEDDING", meta={"progress": "Creating semantic vector..."})
    
    try:
        embedding = deepgram_integration.get_interaction_embedding(extracted_interests)
        
        logger.info(f"[job_id={job_id}] Embedding created ({len(embedding)} dims)")
        
        return {
            **transcription_result,
            "embedding": embedding,
            "embedding_dims": len(embedding),
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Embedding failed: {e}")
        self.update_state(
            state="EMBEDDING_FAILED",
            meta={"error": str(e)}
        )
        raise


@app.task(bind=True, name="src.tasks.transcription_tasks.store_conversation")
def store_conversation(self, transcription_result: dict):
    """Store conversation record in database.
    
    Args:
        transcription_result: Dict with user_id, extracted_interests, mode
        
    Returns:
        Conversation ID
    """
    user_id = transcription_result.get("user_id")
    job_id = transcription_result.get("job_id")
    extracted_interests = transcription_result.get("extracted_interests", "")
    mode = transcription_result.get("mode", "recap")
    
    logger.info(f"[job_id={job_id}] Storing conversation")
    
    try:
        db = SessionLocal()
        conversation = Conversation(
            user_id=user_id,
            transcript=extracted_interests,
            metadata=f"mode={mode},job_id={job_id}",
        )
        db.add(conversation)
        db.commit()
        conversation_id = conversation.id
        db.close()
        
        logger.info(f"[job_id={job_id}] Conversation stored (id={conversation_id})")
        
        return {
            **transcription_result,
            "conversation_id": conversation_id,
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Failed to store conversation: {e}")
        raise
