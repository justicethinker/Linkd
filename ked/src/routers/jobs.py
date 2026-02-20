import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..services.job_queue import JobQueueService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: int  # 0-100
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@router.get("/status/{job_id}")
def get_job_status(
    user_id: int,
    job_id: str,
) -> JobStatusResponse:
    """Get the status of an async job.
    
    Args:
        user_id: User ID (for verification)
        job_id: Job ID to check
        
    Returns:
        Job status with progress and result if available
    """
    status_dict = JobQueueService.get_job_status(job_id, user_id)
    
    if status_dict.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(**status_dict)


@router.get("/list")
def list_user_jobs(
    user_id: int,
    status: str = None,  # "pending", "processing", "completed", "failed"
    limit: int = 50,
):
    """List jobs for a user.
    
    Args:
        user_id: User ID
        status: Optional status filter
        limit: Max results
        
    Returns:
        List of job summaries
    """
    jobs = JobQueueService.get_user_jobs(user_id, status, limit)
    return {
        "user_id": user_id,
        "count": len(jobs),
        "jobs": jobs,
    }


@router.get("/")
def get_jobs_overview(user_id: int):
    """Get overview of user's jobs by status.
    
    Args:
        user_id: User ID
        
    Returns:
        Job count breakdown by status
    """
    pending = JobQueueService.get_user_jobs(user_id, "pending", 1000)
    processing = JobQueueService.get_user_jobs(user_id, "processing", 1000)
    completed = JobQueueService.get_user_jobs(user_id, "completed", 1000)
    failed = JobQueueService.get_user_jobs(user_id, "failed", 1000)
    
    return {
        "user_id": user_id,
        "pending_count": len(pending),
        "processing_count": len(processing),
        "completed_count": len(completed),
        "failed_count": len(failed),
        "total": len(pending) + len(processing) + len(completed) + len(failed),
    }
