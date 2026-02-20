import logging
import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from .. import models, db
from ..services import onboarding_service
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])
genai.configure(api_key=settings.gemini_api_key)


class PersonaResponse(BaseModel):
    id: int
    user_id: int
    label: str
    weight: int

    class Config:
        from_attributes = True


class PersonaPatchRequest(BaseModel):
    label: Optional[str] = None
    weight: Optional[int] = None


def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _get_embedding(text: str) -> list[float]:
    """Get a 1536-dimensional embedding using Google Gemini's embedding API.
    
    Gemini embeddings are 768-dimensional by default; we pad them to 1536
    for compatibility with the database schema (pgvector Vector(1536)).
    """
    try:
        response = genai.embed_content(
            model="models/embedding-001",
            content=text,
        )
        embedding = response["embedding"]
        # Pad from 768 to 1536 dimensions
        padded = embedding + [0.0] * (1536 - len(embedding))
        return padded
    except Exception as e:
        logger.error(f"Failed to get embedding: {e}")
        # Return zero vector as fallback
        return [0.0] * 1536


@router.post("/voice-pitch")
async def ingest_voice_pitch(
    user_id: int,
    file: UploadFile,
    db_session: Session = Depends(get_db),
):
    """Ingest a 60-second voice pitch and create persona nodes.

    Args:
        user_id: the user's ID
        file: audio file (WAV format)

    Returns:
        List of created persona nodes with embeddings
    """
    import tempfile
    import os

    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Ingest and create personas
        personas = onboarding_service.ingest_voice_pitch(user_id, tmp_path, db_session)

        # Get embeddings for each persona
        for persona_node in personas:
            embedding = _get_embedding(persona_node["label"])
            # Update the persona with embedding in DB
            db_persona = db_session.query(models.UserPersona).filter(
                models.UserPersona.user_id == user_id,
                models.UserPersona.label == persona_node["label"],
            ).order_by(models.UserPersona.id.desc()).first()
            if db_persona:
                db_persona.vector = embedding
                db_session.commit()

        logger.info(f"[user_id={user_id}] Created {len(personas)} personas from voice pitch")
        return {"user_id": user_id, "personas_created": len(personas), "personas": personas}
    finally:
        os.unlink(tmp_path)


@router.post("/linkedin-profile")
async def ingest_linkedin_profile(
    user_id: int,
    profile_url: str = Form(...),
    db_session: Session = Depends(get_db),
):
    """Ingest a LinkedIn profile and create persona nodes.

    Args:
        user_id: the user's ID
        profile_url: LinkedIn profile URL

    Returns:
        List of created persona nodes
    """
    # Ingest profile and create personas
    personas = onboarding_service.ingest_linkedin_profile(user_id, profile_url, db_session)

    # Get embeddings for each persona
    for persona_node in personas:
        embedding = _get_embedding(persona_node["label"])
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


@router.get("/persona")
def get_personas(user_id: int, db_session: Session = Depends(get_db)):
    """Get all personas for a user."""
    personas = db_session.query(models.UserPersona).filter(
        models.UserPersona.user_id == user_id
    ).all()
    return [PersonaResponse.from_orm(p) for p in personas]


@router.get("/persona/{persona_id}")
def get_persona(persona_id: int, user_id: int, db_session: Session = Depends(get_db)):
    """Get a specific persona."""
    persona = db_session.query(models.UserPersona).filter(
        models.UserPersona.id == persona_id,
        models.UserPersona.user_id == user_id,
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return PersonaResponse.from_orm(persona)


@router.patch("/persona/{persona_id}")
def update_persona(
    persona_id: int,
    user_id: int,
    update: PersonaPatchRequest,
    db_session: Session = Depends(get_db),
):
    """Update a persona (label and/or weight)."""
    persona = db_session.query(models.UserPersona).filter(
        models.UserPersona.id == persona_id,
        models.UserPersona.user_id == user_id,
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    if update.label is not None:
        persona.label = update.label
        # Re-embed if label changed
        persona.vector = _get_embedding(update.label)
    if update.weight is not None:
        persona.weight = update.weight

    db_session.commit()
    logger.info(f"[user_id={user_id}] Updated persona {persona_id}")
    return PersonaResponse.from_orm(persona)


@router.delete("/persona/{persona_id}")
def delete_persona(
    persona_id: int,
    user_id: int,
    db_session: Session = Depends(get_db),
):
    """Delete a persona."""
    persona = db_session.query(models.UserPersona).filter(
        models.UserPersona.id == persona_id,
        models.UserPersona.user_id == user_id,
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    db_session.delete(persona)
    db_session.commit()
    logger.info(f"[user_id={user_id}] Deleted persona {persona_id}")
    return {"status": "deleted", "persona_id": persona_id}
