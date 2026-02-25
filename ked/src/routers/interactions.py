import logging
import tempfile
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .. import db, models
from ..services import deepgram_integration, overlap
from ..config import settings
from ..auth import get_current_user
from ..exceptions import ValidationError, ExternalServiceError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interactions", tags=["interactions"])


def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _validate_file_size(file_size: int) -> None:
    """Validate file size doesn't exceed limit."""
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        raise ValidationError(
            f"File size exceeds maximum ({settings.max_upload_size_mb}MB)",
            {"max_size_mb": settings.max_upload_size_mb},
        )


@router.post("/process-audio", response_model=dict, status_code=status.HTTP_200_OK)
async def process_interaction_audio(
    file: UploadFile,
    mode: str = Form("recap"),
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Process a recorded interaction (audio) and return interest overlaps.

    Args:
        file: audio file upload
        mode: 'live' (diarized - extract other speaker) or 'recap' (entity extraction)
        user_id: Extracted from JWT token

    Returns:
        Top 3 interest overlaps with similarity scores
        
    Raises:
        ValidationError: If input is invalid
        ExternalServiceError: If processing fails
    """
    if mode not in ["live", "recap"]:
        raise ValidationError(f"Invalid mode: {mode}. Must be 'live' or 'recap'")
    
    if not file.filename or not file.filename.endswith(('.wav', '.mp3', '.ogg')):
        raise ValidationError("File must be an audio file (WAV, MP3, or OGG)")
    
    if file.size:
        _validate_file_size(file.size)

    tmp_path = None
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            _validate_file_size(len(content))
            tmp.write(content)
            tmp_path = tmp.name

        # Process the audio
        extracted_interests = deepgram_integration.process_interaction_audio(tmp_path, mode=mode)
        logger.info(f"[user_id={user_id}] Extracted interests from {mode} mode: {extracted_interests[:100]}...")

        # Create real embedding from extracted interests
        embedding = deepgram_integration.get_interaction_embedding(extracted_interests)
        logger.debug(f"[user_id={user_id}] Created embedding vector ({len(embedding)} dims)")

        # Find overlaps with user's personas
        synapses = overlap.compute_top_synapses(user_id, embedding, threshold=0.7, top_k=3)

        # Log the interaction (store transcript + metadata)
        conversation = models.Conversation(
            user_id=user_id,
            transcript=extracted_interests,
            conversation_metadata=f"mode={mode}",
        )
        db_session.add(conversation)
        db_session.commit()
        
        logger.info(f"[user_id={user_id}] Processed interaction: {mode} mode, found {len(synapses)} synapses")

        return {
            "user_id": user_id,
            "mode": mode,
            "extracted_interests": extracted_interests,
            "top_synapses": synapses,
            "conversation_id": conversation.id,
        }
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to process audio: {e}")
        raise ExternalServiceError("Audio Processing", str(e))
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp_path}: {e}")
