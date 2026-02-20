import logging
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import Job
from ..db import SessionLocal

logger = logging.getLogger(__name__)


class JobQueueService:
    """Manage async jobs (create, update, retrieve status)."""

    @staticmethod
    def create_job(user_id: int, job_type: str, input_data: dict = None) -> str:
        """Create a new job and return its ID.
        
        Args:
            user_id: User ID
            job_type: Type of job ("onboarding", "interaction", etc.)
            input_data: Optional input data as dict
            
        Returns:
            job_id (UUID string)
        """
        db = SessionLocal()
        try:
            job_id = str(uuid.uuid4())
            job = Job(
                job_id=job_id,
                user_id=user_id,
                job_type=job_type,
                status="pending",
                input_data=json.dumps(input_data) if input_data else None,
                progress=0,
            )
            db.add(job)
            db.commit()
            logger.info(f"[user_id={user_id}] Created job {job_id} (type={job_type})")
            return job_id
        finally:
            db.close()

    @staticmethod
    def get_job_status(job_id: str, user_id: int = None) -> dict:
        """Get job status.
        
        Args:
            job_id: Job ID
            user_id: Optional user ID for verification
            
        Returns:
            Job status dict with status, progress, result, error
        """
        db = SessionLocal()
        try:
            query = db.query(Job).filter(Job.job_id == job_id)
            if user_id:
                query = query.filter(Job.user_id == user_id)
            
            job = query.first()
            if not job:
                return {"status": "not_found", "error": "Job not found"}
            
            return {
                "job_id": job.job_id,
                "status": job.status,
                "progress": job.progress,
                "result": json.loads(job.result) if job.result else None,
                "error": job.error_message,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
        finally:
            db.close()

    @staticmethod
    def start_job(job_id: str) -> None:
        """Mark job as processing."""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                job.status = "processing"
                job.started_at = datetime.utcnow()
                job.progress = 10
                db.commit()
                logger.info(f"Started job {job_id}")
        finally:
            db.close()

    @staticmethod
    def update_job_progress(job_id: str, progress: int) -> None:
        """Update job progress (0-100)."""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                job.progress = max(0, min(100, progress))
                db.commit()
        finally:
            db.close()

    @staticmethod
    def complete_job(job_id: str, result: dict) -> None:
        """Mark job as completed with result."""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                job.status = "completed"
                job.result = json.dumps(result)
                job.progress = 100
                job.completed_at = datetime.utcnow()
                db.commit()
                logger.info(f"Completed job {job_id}")
        finally:
            db.close()

    @staticmethod
    def fail_job(job_id: str, error_message: str) -> None:
        """Mark job as failed with error message."""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = error_message
                job.completed_at = datetime.utcnow()
                db.commit()
                logger.error(f"Failed job {job_id}: {error_message}")
        finally:
            db.close()

    @staticmethod
    def get_user_jobs(user_id: int, status: str = None, limit: int = 50) -> list:
        """Get recent jobs for a user.
        
        Args:
            user_id: User ID
            status: Optional status filter ("pending", "processing", "completed", "failed")
            limit: Max results
            
        Returns:
            List of job dicts
        """
        db = SessionLocal()
        try:
            query = db.query(Job).filter(Job.user_id == user_id)
            if status:
                query = query.filter(Job.status == status)
            
            jobs = query.order_by(Job.created_at.desc()).limit(limit).all()
            return [
                {
                    "job_id": j.job_id,
                    "type": j.job_type,
                    "status": j.status,
                    "progress": j.progress,
                    "created_at": j.created_at.isoformat(),
                }
                for j in jobs
            ]
        finally:
            db.close()
