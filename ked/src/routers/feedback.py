import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from .. import models, db
from ..services.metrics_service import MetricsService
from ..auth import get_current_user
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    feedback_type: str = Field(..., pattern="^(approved|rejected|rated)$")  # "approved", "rejected", "rated"
    rating: Optional[int] = Field(None, ge=1, le=5)  # 1-5 stars
    notes: Optional[str] = Field(None, max_length=500)


class MetricsResponse(BaseModel):
    total_interactions: int
    avg_extraction_accuracy: float
    approval_rate: float
    avg_processing_time_ms: float
    avg_top_similarity: float
    total_approved: int
    total_rejected: int


def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.post("/persona/{persona_id}", status_code=status.HTTP_200_OK)
def submit_persona_feedback(
    persona_id: int,
    feedback: FeedbackRequest,
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Submit feedback on a persona node (approve, reject, or rate).
    
    Args:
        persona_id: Persona ID
        feedback: FeedbackRequest with feedback_type and optional rating/notes
        user_id: Extracted from JWT token
        
    Returns:
        Feedback confirmation
        
    Raises:
        ValidationError: If feedback is invalid
    """
    if feedback.feedback_type == "rated" and not feedback.rating:
        raise ValidationError("Rating required for 'rated' feedback type")
    
    # Verify persona belongs to user
    persona = db_session.query(models.UserPersona).filter(
        models.UserPersona.id == persona_id,
        models.UserPersona.user_id == user_id,
    ).first()
    
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    try:
        # Create feedback record
        feedback_record = models.PersonaFeedback(
            user_id=user_id,
            persona_id=persona_id,
            feedback_type=feedback.feedback_type,
            rating=feedback.rating,
            notes=feedback.notes,
        )
        db_session.add(feedback_record)
        
        # If rejected, optionally decrease weight
        if feedback.feedback_type == "rejected" and persona.weight > 1:
            persona.weight = max(1, persona.weight - 1)
        # If approved, increase weight
        elif feedback.feedback_type == "approved" and persona.weight < 10:
            persona.weight = min(10, persona.weight + 1)
        
        db_session.commit()
        logger.info(f"[user_id={user_id}] Feedback on persona {persona_id}: {feedback.feedback_type}")
        
        return {
            "status": "recorded",
            "persona_id": persona_id,
            "feedback_type": feedback.feedback_type,
            "new_weight": persona.weight,
        }
    except Exception as e:
        db_session.rollback()
        logger.error(f"[user_id={user_id}] Failed to submit feedback: {e}")
        raise


@router.get("/persona/{persona_id}")
def get_persona_feedback(
    persona_id: int,
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Get feedback history for a persona.
    
    Args:
        persona_id: Persona ID
        user_id: Extracted from JWT token
        
    Returns:
        Feedback history
    """
    feedback_records = db_session.query(models.PersonaFeedback).filter(
        models.PersonaFeedback.persona_id == persona_id,
        models.PersonaFeedback.user_id == user_id,
    ).all()
    
    return {
        "persona_id": persona_id,
        "feedback_count": len(feedback_records),
        "feedback": [
            {
                "id": f.id,
                "type": f.feedback_type,
                "rating": f.rating,
                "notes": f.notes,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in feedback_records
        ],
    }


@router.get("/metrics", response_model=MetricsResponse)
def get_user_metrics(
    user_id: int = Depends(get_current_user),
):
    """Get aggregated metrics for a user.
    
    Args:
        user_id: Extracted from JWT token
        
    Returns:
        User metrics
    """
    try:
        metrics = MetricsService.get_user_metrics(user_id)
        logger.info(f"[user_id={user_id}] Retrieved metrics")
        return MetricsResponse(**metrics)
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")
        user_id: User ID
        persona_id: Persona ID
        
    Returns:
        List of feedback records
    """
    # Verify persona belongs to user
    persona = db_session.query(models.UserPersona).filter(
        models.UserPersona.id == persona_id,
        models.UserPersona.user_id == user_id,
    ).first()
    
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    feedbacks = db_session.query(models.PersonaFeedback).filter(
        models.PersonaFeedback.persona_id == persona_id,
    ).order_by(models.PersonaFeedback.created_at.desc()).all()
    
    return [
        {
            "feedback_type": f.feedback_type,
            "rating": f.rating,
            "notes": f.notes,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedbacks
    ]


@router.post("/interaction/{metric_id}")
def submit_interaction_feedback(
    user_id: int,
    metric_id: int,
    approved_count: int,
    rejected_count: int,
    db_session: Session = Depends(get_db),
):
    """Submit feedback on interaction results (approved/rejected synapse count).
    
    Args:
        user_id: User ID
        metric_id: Metric ID from interaction
        approved_count: Number of approved synapses
        rejected_count: Number of rejected synapses
        
    Returns:
        Feedback confirmation
    """
    # Verify metric belongs to user
    metric = db_session.query(models.InteractionMetric).filter(
        models.InteractionMetric.id == metric_id,
        models.InteractionMetric.user_id == user_id,
    ).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    MetricsService.record_feedback(metric_id, approved_count, rejected_count)
    logger.info(
        f"[user_id={user_id}] Interaction feedback: "
        f"approved={approved_count}, rejected={rejected_count}"
    )
    
    return {
        "status": "recorded",
        "metric_id": metric_id,
        "approved": approved_count,
        "rejected": rejected_count,
        "accuracy": metric.extraction_accuracy,
    }


@router.get("/metrics")
def get_user_metrics(
    user_id: int,
    mode: str = None,  # "live" or "recap"
    db_session: Session = Depends(get_db),
) -> MetricsResponse:
    """Get user's accuracy and performance metrics.
    
    Args:
        user_id: User ID
        mode: Optional mode filter
        
    Returns:
        Metrics summary
    """
    summary = MetricsService.get_accuracy_summary(user_id)
    return MetricsResponse(**summary)


@router.get("/metrics/interactions")
def get_interaction_metrics(
    user_id: int,
    mode: str = None,
    limit: int = 50,
    db_session: Session = Depends(get_db),
):
    """Get detailed metrics for recent interactions.
    
    Args:
        user_id: User ID
        mode: Optional mode filter ("live" or "recap")
        limit: Max results
        
    Returns:
        List of interaction metrics
    """
    metrics = MetricsService.get_user_metrics(user_id, mode, limit)
    return {"count": len(metrics), "metrics": metrics}
