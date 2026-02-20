import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form
from sqlalchemy.orm import Session
from typing import Optional

from .. import db, models
from ..services import deepgram_integration, overlap

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interactions", tags=["interactions"])


def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.post("/process-audio")
async def process_interaction_audio(
    user_id: int,
    file: UploadFile,
    mode: str = Form("recap"),
    db_session: Session = Depends(get_db),
):
    """Process a recorded interaction (audio) and return interest overlaps.

    Args:
        user_id: the user processing the interaction
        file: audio file upload
        mode: 'live' (diarized - extract other speaker) or 'recap' (entity extraction)

    Returns:
        Top 3 interest overlaps with similarity scores.
    """
    # Save uploaded file temporarily
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Process the audio
        extracted_interests = deepgram_integration.process_interaction_audio(tmp_path, mode=mode)
        logger.info(f"[user_id={user_id}] Extracted interests: {extracted_interests[:100]}...")

        # Create real embedding from extracted interests (Semantic Overlap Engine - Step 3: Embed)
        embedding = deepgram_integration.get_interaction_embedding(extracted_interests)
        logger.debug(f"[user_id={user_id}] Created embedding vector ({len(embedding)} dims)")

        # Find overlaps with user's personas (Semantic Overlap Engine - Step 4: Match)
        synapses = overlap.compute_top_synapses(user_id, embedding, threshold=0.7, top_k=3)

        # Log the interaction (store transcript + metadata)
        conversation = models.Conversation(
            user_id=user_id,
            transcript=extracted_interests,
            metadata=f"mode={mode}",
        )
        db_session.add(conversation)
        db_session.commit()

        return {
            "user_id": user_id,
            "mode": mode,
            "extracted_interests": extracted_interests,
            "top_synapses": synapses,
            "conversation_id": conversation.id,
        }
    finally:
        # Clean up temp file
        os.unlink(tmp_path)
