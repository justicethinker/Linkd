import logging
import tempfile
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .. import models, db
from ..services import onboarding_service
from ..config import settings
from ..auth import get_current_user
from ..exceptions import ValidationError, ExternalServiceError
import google.genai

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Initialize Google Genai client
genai.configure(api_key=settings.gemini_api_key)
client = genai.Client(api_key=settings.gemini_api_key)


class PersonaResponse(BaseModel):
    id: int
    user_id: int
    label: str
    weight: int

    class Config:
        from_attributes = True


class PersonaPatchRequest(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=500)
    weight: Optional[int] = Field(None, ge=1, le=10)


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
            {"max_size_mb": settings.max_upload_size_mb, "file_size_bytes": file_size},
        )


async def _get_embedding(text: str) -> list[float]:
    """Get a 1536-dimensional embedding using Google Genai's embedding API.
    
    Args:
        text: Text to embed
        
    Returns:
        1536-dimensional embedding vector
        
    Raises:
        ExternalServiceError: If embedding fails
    """
    try:
        if not text or not text.strip():
            raise ValidationError("Text to embed cannot be empty")
        
        # Use google.genai for embeddings
        response = client.models.embed_content(
            model="models/text-embedding-004",
            content=text,
        )
        embedding = response.embedding
        
        # Ensure 1536 dimensions (pad or truncate as needed)
        if len(embedding) < 1536:
            embedding = embedding + [0.0] * (1536 - len(embedding))
        elif len(embedding) > 1536:
            embedding = embedding[:1536]
            
        logger.debug(f"Generated embedding with {len(embedding)} dimensions")
        return embedding
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Failed to get embedding: {e}")
        raise ExternalServiceError("Google Genai", f"Embedding failed: {str(e)}")


@router.post("/voice-pitch", response_model=dict, status_code=status.HTTP_201_CREATED)
async def ingest_voice_pitch(
    file: UploadFile,
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Ingest a 60-second voice pitch and create persona nodes.

    Args:
        file: audio file (WAV format)
        user_id: Extracted from JWT token

    Returns:
        List of created persona nodes with embeddings
        
    Raises:
        ValidationError: If file size exceeds limit
        ExternalServiceError: If processing fails
    """
    # Validate file size
    if not file.filename or not file.filename.endswith(('.wav', '.mp3', '.ogg')):
        raise ValidationError("File must be an audio file (WAV, MP3, or OGG)")
    
    if file.size:
        _validate_file_size(file.size)

    tmp_path = None
    try:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            _validate_file_size(len(content))
            tmp.write(content)
            tmp_path = tmp.name

        # Ingest and create personas
        personas = onboarding_service.ingest_voice_pitch(user_id, tmp_path, db_session)

        # Get embeddings for each persona
        for persona_node in personas:
            embedding = await _get_embedding(persona_node["label"])
            # Update the persona with embedding in DB
            db_persona = db_session.query(models.UserPersona).filter(
                models.UserPersona.user_id == user_id,
                models.UserPersona.label == persona_node["label"],
            ).order_by(models.UserPersona.id.desc()).first()
            if db_persona:
                db_persona.vector = embedding
                db_session.commit()

        return {"user_id": user_id, "personas_created": len(personas), "personas": personas}
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to ingest voice pitch: {e}")
        raise ExternalServiceError("Voice Processing", str(e))
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp_path}: {e}")


@router.post("/linkedin-profile", response_model=dict, status_code=status.HTTP_201_CREATED)
async def ingest_linkedin_profile(
    profile_url: str = Form(...),
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Ingest a LinkedIn profile and create persona nodes.

    Args:
        profile_url: LinkedIn profile URL
        user_id: Extracted from JWT token

    Returns:
        List of created persona nodes
        
    Raises:
        ValidationError: If URL is invalid
        ExternalServiceError: If processing fails
    """
    if not profile_url or not profile_url.startswith("https://linkedin.com"):
        raise ValidationError("Invalid LinkedIn profile URL")

    try:
        # Ingest profile and create personas
        personas = await onboarding_service.ingest_linkedin_profile(user_id, profile_url, db_session)

        # Get embeddings for each persona
        for persona_node in personas:
            embedding = await _get_embedding(persona_node["label"])
            # Update the persona with embedding in DB
            db_persona = db_session.query(models.UserPersona).filter(
                models.UserPersona.user_id == user_id,
                models.UserPersona.label == persona_node["label"],
            ).order_by(models.UserPersona.id.desc()).first()
            if db_persona:
                db_persona.vector = embedding
                db_session.commit()

        logger.info(f"[user_id={user_id}] Created {len(personas)} personas from LinkedIn")
        return {"user_id": user_id, "personas_created": len(personas), "personas": personas}
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to ingest LinkedIn profile: {e}")
        raise ExternalServiceError("LinkedIn", str(e))


@router.get("/persona", response_model=list[PersonaResponse])
def get_personas(
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Get all personas for a user."""
    personas = db_session.query(models.UserPersona).filter(
        models.UserPersona.user_id == user_id
    ).all()
    logger.info(f"[user_id={user_id}] Retrieved {len(personas)} personas")
    return [PersonaResponse.from_orm(p) for p in personas]


@router.get("/persona/{persona_id}", response_model=PersonaResponse)
def get_persona(
    persona_id: int,
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Get a specific persona."""
    persona = db_session.query(models.UserPersona).filter(
        models.UserPersona.id == persona_id,
        models.UserPersona.user_id == user_id,
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return PersonaResponse.from_orm(persona)


@router.patch("/persona/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: int,
    update: PersonaPatchRequest,
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Update a persona (label and/or weight)."""
    persona = db_session.query(models.UserPersona).filter(
        models.UserPersona.id == persona_id,
        models.UserPersona.user_id == user_id,
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    try:
        if update.label is not None:
            persona.label = update.label
            # Re-embed if label changed
            persona.vector = await _get_embedding(update.label)
        if update.weight is not None:
            persona.weight = update.weight

        db_session.commit()
        logger.info(f"[user_id={user_id}] Updated persona {persona_id}")
        return PersonaResponse.from_orm(persona)
    except Exception as e:
        db_session.rollback()
        logger.error(f"[user_id={user_id}] Failed to update persona {persona_id}: {e}")
        raise ExternalServiceError("Persona Update", str(e))


@router.delete("/persona/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(
    persona_id: int,
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Delete a persona."""
    persona = db_session.query(models.UserPersona).filter(
        models.UserPersona.id == persona_id,
        models.UserPersona.user_id == user_id,
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    try:
        db_session.delete(persona)
        db_session.commit()
        logger.info(f"[user_id={user_id}] Deleted persona {persona_id}")
    except Exception as e:
        db_session.rollback()
        logger.error(f"[user_id={user_id}] Failed to delete persona {persona_id}: {e}")
        raise ExternalServiceError("Persona Delete", str(e))
