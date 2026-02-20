import logging
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import InteractionMetric
from ..db import SessionLocal

logger = logging.getLogger(__name__)


class MetricsService:
    """Track interaction accuracy and performance metrics."""

    @staticmethod
    def record_interaction_metrics(
        user_id: int,
        interaction_id: int,
        mode: str,
        synapses: list,
        processing_time_ms: int,
    ) -> int:
        """Record metrics for an interaction.
        
        Args:
            user_id: User ID
            interaction_id: Conversation ID
            mode: "live" or "recap"
            synapses: List of synapse matches with similarity scores
            processing_time_ms: Total processing time in milliseconds
            
        Returns:
            metric_id
        """
        db = SessionLocal()
        try:
            similarities = [s.get("similarity", 0) for s in synapses]
            top_similarity = similarities[0] if similarities else 0
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0
            
            metric = InteractionMetric(
                user_id=user_id,
                interaction_id=interaction_id,
                mode=mode,
                top_synapse_similarity=top_similarity,
                avg_similarity=avg_similarity,
                processing_time_ms=processing_time_ms,
            )
            db.add(metric)
            db.commit()
            
            logger.info(
                f"[user_id={user_id}] Recorded metrics: "
                f"mode={mode}, top_sim={top_similarity:.2f}, avg_sim={avg_similarity:.2f}, time={processing_time_ms}ms"
            )
            return metric.id
        finally:
            db.close()

    @staticmethod
    def update_accuracy(metric_id: int, accuracy_score: float) -> None:
        """Update extraction accuracy score (0-100%).
        
        Args:
            metric_id: Metric ID
            accuracy_score: Accuracy percentage (0-100)
        """
        db = SessionLocal()
        try:
            metric = db.query(InteractionMetric).filter(InteractionMetric.id == metric_id).first()
            if metric:
                metric.extraction_accuracy = max(0, min(100, accuracy_score))
                db.commit()
        finally:
            db.close()

    @staticmethod
    def record_feedback(metric_id: int, approved_count: int, rejected_count: int) -> None:
        """Record user feedback on extracted synapses.
        
        Args:
            metric_id: Metric ID
            approved_count: Number of approved synapses
            rejected_count: Number of rejected synapses
        """
        db = SessionLocal()
        try:
            metric = db.query(InteractionMetric).filter(InteractionMetric.id == metric_id).first()
            if metric:
                metric.user_approved = approved_count
                metric.user_rejected = rejected_count
                # Calculate accuracy from feedback
                total = approved_count + rejected_count
                if total > 0:
                    accuracy = (approved_count / total) * 100
                    metric.extraction_accuracy = accuracy
                db.commit()
        finally:
            db.close()

    @staticmethod
    def get_user_metrics(user_id: int, mode: str = None, limit: int = 100) -> list:
        """Get metrics for user interactions.
        
        Args:
            user_id: User ID
            mode: Optional mode filter ("live" or "recap")
            limit: Max results
            
        Returns:
            List of metric dicts
        """
        db = SessionLocal()
        try:
            query = db.query(InteractionMetric).filter(InteractionMetric.user_id == user_id)
            if mode:
                query = query.filter(InteractionMetric.mode == mode)
            
            metrics = query.order_by(InteractionMetric.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": m.id,
                    "mode": m.mode,
                    "top_similarity": m.top_synapse_similarity,
                    "avg_similarity": m.avg_similarity,
                    "accuracy": m.extraction_accuracy,
                    "time_ms": m.processing_time_ms,
                    "approved": m.user_approved,
                    "rejected": m.user_rejected,
                    "created_at": m.created_at.isoformat(),
                }
                for m in metrics
            ]
        finally:
            db.close()

    @staticmethod
    def get_accuracy_summary(user_id: int) -> dict:
        """Get accuracy statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Summary dict with avg accuracy, approved rate, etc.
        """
        db = SessionLocal()
        try:
            metrics = db.query(InteractionMetric).filter(InteractionMetric.user_id == user_id).all()
            
            if not metrics:
                return {"total_interactions": 0}
            
            accuracies = [m.extraction_accuracy for m in metrics if m.extraction_accuracy]
            avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
            
            total_approved = sum(m.user_approved for m in metrics)
            total_rejected = sum(m.user_rejected for m in metrics)
            total_feedback = total_approved + total_rejected
            approval_rate = (total_approved / total_feedback * 100) if total_feedback > 0 else 0
            
            avg_time = sum(m.processing_time_ms for m in metrics) / len(metrics)
            avg_top_similarity = sum(m.top_synapse_similarity for m in metrics) / len(metrics)
            
            return {
                "total_interactions": len(metrics),
                "avg_extraction_accuracy": round(avg_accuracy, 2),
                "approval_rate": round(approval_rate, 2),
                "avg_processing_time_ms": round(avg_time, 0),
                "avg_top_similarity": round(avg_top_similarity, 3),
                "total_approved": total_approved,
                "total_rejected": total_rejected,
            }
        finally:
            db.close()
