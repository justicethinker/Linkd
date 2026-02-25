import logging
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional

from ..services.job_queue import JobQueueService
from ..auth import get_current_user
from ..exceptions import NotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobStatusResponse(BaseModel):
    job_id: str
    status: str = Field(..., pattern="^(pending|processing|completed|failed)$")
    progress: int = Field(..., ge=0, le=100)
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@router.get("/status/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    user_id: int = Depends(get_current_user),
) -> JobStatusResponse:
    """Get the status of an async job.
    
    Args:
        job_id: Job ID to check
        user_id: Extracted from JWT token (for verification)
        
    Returns:
        Job status with progress and result if available
        
    Raises:
        NotFoundError: If job not found
    """
    try:
        status_dict = JobQueueService.get_job_status(job_id, user_id)
        
        if status_dict.get("status") == "not_found":
            raise NotFoundError(f"Job {job_id} not found")
        
        logger.info(f"[user_id={user_id}] Retrieved job status: {job_id}")
        return JobStatusResponse(**status_dict)
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to get job status: {e}")
        raise


@router.get("/list", status_code=status.HTTP_200_OK)
def list_user_jobs(
    user_id: int = Depends(get_current_user),
    status_filter: str = None,  # "pending", "processing", "completed", "failed"
    limit: int = Field(50, ge=1, le=500),
):
    """List jobs for a user.
    
    Args:
        user_id: Extracted from JWT token
        status_filter: Optional status filter
        limit: Max results (1-500)
        
    Returns:
        List of job summaries
        
    Raises:
        ValidationError: If status filter is invalid
    """
    valid_statuses = ["pending", "processing", "completed", "failed"]
    if status_filter and status_filter not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )
    
    try:
        jobs = JobQueueService.get_user_jobs(user_id, status_filter, limit)
        logger.info(f"[user_id={user_id}] Retrieved {len(jobs)} jobs")
        return {
            "user_id": user_id,
            "count": len(jobs),
            "jobs": jobs,
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@router.get("/", status_code=status.HTTP_200_OK)
def get_jobs_overview(user_id: int = Depends(get_current_user)):
    """Get overview of user's jobs by status.
    
    Args:
        user_id: Extracted from JWT token
        
    Returns:
        Job count breakdown by status
    """
    try:
        pending = JobQueueService.get_user_jobs(user_id, "pending", 1000)
        processing = JobQueueService.get_user_jobs(user_id, "processing", 1000)
        completed = JobQueueService.get_user_jobs(user_id, "completed", 1000)
        failed = JobQueueService.get_user_jobs(user_id, "failed", 1000)
        
        logger.info(f"[user_id={user_id}] Retrieved jobs overview")
        return {
            "user_id": user_id,
            "pending_count": len(pending),
            "processing_count": len(processing),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "total": len(pending) + len(processing) + len(completed) + len(failed),
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to get jobs overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to get jobs overview")
