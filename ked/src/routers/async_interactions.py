"""Phase 2: Async interaction processing with state machine.

Provides endpoints for submitting interactions and polling workflow status.
Uses Celery for distributed task processing with multi-stage state tracking.

State Machine: PENDING → TRANSCRIPTION → ENRICHMENT → SYNTHESIS → SUCCESS
              └─→ ERROR at any stage
"""

import logging
import json
import tempfile
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from .. import db
from ..services import storage_service
from ..workflows import start_interaction_workflow, get_workflow_status, cancel_workflow
from ..models import Job
from ..auth import get_current_user
from ..exceptions import ValidationError, ExternalServiceError
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v2", tags=["async-interactions"])

storage = storage_service.S3StorageService()


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


class InteractionSubmitRequest(BaseModel):
    """Request to submit an interaction for async processing."""
    mode: str = Field("recap", pattern="^(live|recap)$")  # 'live' or 'recap'
    

class WorkflowStatusResponse(BaseModel):
    """Response containing workflow status and progress."""
    job_id: str
    task_id: str
    state: str = Field(..., pattern="^(PENDING|TRANSCRIPTION|ENRICHMENT|SYNTHESIS|SUCCESS|ERROR)$")
    progress: str
    result: Optional[dict] = None
    error: Optional[str] = None


@router.post("/interactions/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_interaction_async(
    file: UploadFile,
    mode: str = Form("recap"),
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
) -> dict:
    """Submit an interaction for asynchronous distributed processing.
    
    This endpoint starts the complete Phase 2 workflow:
    1. Stores audio in S3 (with 24-hour expiration)
    2. Creates a Job tracking record
    3. Starts the Celery workflow (transcription → enrichment → synthesis)
    
    Returns immediately with job_id for polling progress.
    
    Args:
        file: Audio file upload
        mode: 'live' (diarized, other speaker extraction) or 'recap' (entity extraction)
        user_id: Extracted from JWT token
        db_session: Database session
        
    Returns:
        {
            "job_id": "uuid-job-id",
            "task_id": "celery-task-id",
            "state": "PENDING",
            "status_url": "/v2/interactions/status/uuid-job-id"
        }
        
    Raises:
        ValidationError: If input is invalid
        ExternalServiceError: If workflow startup fails
    """
    import uuid
    
    if mode not in ["live", "recap"]:
        raise ValidationError(f"Invalid mode: {mode}. Must be 'live' or 'recap'")
    
    if not file.filename or not file.filename.endswith(('.wav', '.mp3', '.ogg')):
        raise ValidationError("File must be an audio file (WAV, MP3, or OGG)")
    
    if file.size:
        _validate_file_size(file.size)
    
    job_id = str(uuid.uuid4())
    tmp_path = None
    logger.info(f"[job_id={job_id}] New async interaction submission (user_id={user_id}, mode={mode})")
    
    try:
        # Save audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            _validate_file_size(len(content))
            tmp.write(content)
            tmp_path = tmp.name
        
        # Upload to S3 with 24-hour expiration metadata
        s3_key = None
        try:
            s3_key = storage.upload_audio_file(user_id, tmp_path, f"{job_id}.wav")
            logger.info(f"[job_id={job_id}] Audio uploaded to S3: {s3_key}")
        except Exception as s3_error:
            logger.warning(f"[job_id={job_id}] S3 upload failed, using local storage: {s3_error}")
        
        # Create Job tracking record
        job = Job(
            job_id=job_id,
            user_id=user_id,
            status="PENDING",
            job_type="interaction",
            input_data=json.dumps({
                "mode": mode,
                "audio_file": tmp_path,
                "s3_key": s3_key,
            }),
            progress=0,
        )
        db_session.add(job)
        db_session.commit()
        logger.info(f"[job_id={job_id}] Job record created")
        
        # Start the distributed workflow
        task_id = start_interaction_workflow(
            user_id=user_id,
            job_id=job_id,
            audio_file_path=tmp_path,
            mode=mode,
        )
        
        # Update job with Celery task ID
        job.job_metadata = json.dumps({"celery_task_id": task_id})
        db_session.commit()
        
        logger.info(f"[job_id={job_id}] Workflow started with task_id={task_id}")
        
        return {
            "job_id": job_id,
            "task_id": task_id,
            "state": "PENDING",
            "status_url": f"/v2/interactions/status/{job_id}",
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Failed to submit interaction: {e}")
        
        # Update job as failed
        try:
            job = db_session.query(Job).filter(Job.job_id == job_id).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                db_session.commit()
        except Exception as db_error:
            logger.warning(f"[job_id={job_id}] Could not update job record: {db_error}")
        
        raise HTTPException(status_code=500, detail=f"Failed to submit interaction: {e}")


@router.get("/interactions/status/{job_id}", response_model=WorkflowStatusResponse)
async def get_interaction_status(job_id: str, db_session: Session = Depends(get_db)):
    """Poll the status of an async interaction workflow.
    
    Returns the current state and progress of the workflow:
    - PENDING: Queued, waiting for workers
    - TRANSCRIPTION: Converting speech to text with Deepgram
    - ENRICHMENT: Scraping LinkedIn, extracting social context
    - SYNTHESIS: Creating final insight and warm outreach draft
    - SUCCESS: Complete, results available
    - ERROR: Failed at some stage
    
    Args:
        job_id: Job ID from submit_interaction response
        db_session: Database session
        
    Returns:
        Workflow status with progress and partial results
        
    Example Response:
        {
            "job_id": "abc-123-def",
            "task_id": "celery-task-abc",
            "state": "ENRICHMENT",
            "progress": "Scraping LinkedIn profiles...",
            "result": null
        }
    """
    logger.info(f"Status check for job_id={job_id}")
    
    try:
        # Get job record
        job = db_session.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Get Celery task ID
        metadata = json.loads(job.job_metadata or "{}")
        celery_task_id = metadata.get("celery_task_id")
        
        if not celery_task_id:
            # Job not started yet
            return WorkflowStatusResponse(
                job_id=job_id,
                task_id="",
                state="PENDING",
                progress="Queued...",
            )
        
        # Get workflow status from Celery
        workflow_status = get_workflow_status(celery_task_id)
        
        return WorkflowStatusResponse(
            job_id=job_id,
            task_id=celery_task_id,
            state=workflow_status["state"],
            progress=workflow_status.get("progress", ""),
            result=workflow_status.get("result"),
            error=workflow_status.get("error"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for job_id={job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


@router.post("/interactions/cancel/{job_id}")
async def cancel_interaction(job_id: str, db_session: Session = Depends(get_db)):
    """Cancel a running interaction workflow.
    
    Args:
        job_id: Job ID to cancel
        
    Returns:
        Success confirmation
    """
    logger.info(f"Cancelling job_id={job_id}")
    
    try:
        # Get job record
        job = db_session.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Cancel Celery task
        metadata = json.loads(job.job_metadata or "{}")
        celery_task_id = metadata.get("celery_task_id")
        
        if celery_task_id:
            cancel_workflow(celery_task_id)
        
        # Update job status
        job.status = "CANCELLED"
        db_session.commit()
        
        logger.info(f"Job {job_id} cancelled")
        
        return {
            "job_id": job_id,
            "state": "CANCELLED",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job_id={job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel: {e}")

# ===== Phase 2b Endpoints: Enhanced multi-source workflows =====


@router.post("/interactions/submit-v2b")
async def submit_interaction_v2b(
    user_id: int,
    file: UploadFile,
    mode: str = Form("recap"),
    sources: str = Form(None),  # Comma-separated list of enabled sources
    db_session: Session = Depends(get_db),
) -> dict:
    """Submit an interaction for Phase 2b asynchronous processing (multi-source).
    
    Enhanced version with multi-source enrichment:
    1. Stores audio in S3
    2. Creates Job tracking record
    3. Starts Phase 2b workflow with source dispatcher
    
    The Phase 2b workflow includes:
    - Source dispatcher: Parallel queries to 6-8 sources (LinkedIn, GitHub, Instagram, TikTok, Twitter, Search, YouTube, Bluesky)
    - Identity resolution: LLM-based confidence scoring to select best candidate
    - Triple-vector synthesis: Fuse transcript + professional + personality embeddings
    - Social quadrant mapping: Map presence across Professional/Creative/Casual/Real-time dimensions
    - Social hooks: Include specific references to found content in outreach
    
    Args:
        user_id: User ID
        file: Audio file upload
        mode: 'live' (diarized) or 'recap' (entity extraction)
        sources: Optional comma-separated list of sources to query
                (Valid: linkedin, instagram, tiktok, github, twitter, search, youtube, bluesky)
        db_session: Database session
        
    Returns:
        {
            "job_id": "uuid-job-id",
            "task_id": "celery-task-id",
            "state": "PENDING",
            "workflow_version": "2b",
            "status_url": "/v2/interactions/status/uuid-job-id",
            "estimated_duration_seconds": 120
        }
    """
    import uuid
    import tempfile
    
    job_id = str(uuid.uuid4())
    enabled_sources = sources.split(",") if sources else None
    
    logger.info(
        f"[job_id={job_id}] Phase 2b interaction submission "
        f"(user_id={user_id}, sources={enabled_sources or 'all'})"
    )
    
    try:
        # Save audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Upload to S3
        try:
            s3_key = storage.upload_audio_file(user_id, tmp_path, f"{job_id}.wav")
            logger.info(f"[job_id={job_id}] Audio uploaded to S3: {s3_key}")
        except Exception as s3_error:
            logger.warning(f"[job_id={job_id}] S3 upload failed, using local: {s3_error}")
            s3_key = None
        
        # Create Job tracking record
        job = Job(
            job_id=job_id,
            user_id=user_id,
            status="PENDING",
            job_type="interaction_v2b",
            input_data=json.dumps({
                "mode": mode,
                "audio_file": tmp_path,
                "s3_key": s3_key,
                "sources": enabled_sources,
            }),
            progress=0,
        )
        db_session.add(job)
        db_session.commit()
        logger.info(f"[job_id={job_id}] Job record created (Phase 2b)")
        
        # Start the Phase 2b workflow
        from ..workflows import start_interaction_workflow_v2b
        
        task_id = start_interaction_workflow_v2b(
            user_id=user_id,
            job_id=job_id,
            audio_file_path=tmp_path,
            mode=mode,
            enabled_sources=enabled_sources,
        )
        
        # Update job with Celery task ID
        job.job_metadata = json.dumps({
            "celery_task_id": task_id,
            "workflow_version": "2b",
        })
        db_session.commit()
        
        logger.info(f"[job_id={job_id}] Phase 2b workflow started with task_id={task_id}")
        
        return {
            "job_id": job_id,
            "task_id": task_id,
            "state": "PENDING",
            "workflow_version": "2b",
            "status_url": f"/v2/interactions/status/{job_id}",
            "estimated_duration_seconds": 120,  # Phase 2b takes longer due to multi-source queries
        }
        
    except Exception as e:
        logger.error(f"[job_id={job_id}] Failed to submit Phase 2b interaction: {e}")
        
        try:
            job = db_session.query(Job).filter(Job.job_id == job_id).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                db_session.commit()
        except Exception as db_error:
            logger.warning(f"[job_id={job_id}] Could not update job: {db_error}")
        
        raise HTTPException(status_code=500, detail=f"Failed to submit interaction: {e}")


class InteractionDetailResponse(BaseModel):
    """Detailed interaction results (Phase 2b)."""
    job_id: str
    task_id: str
    state: str
    workflow_version: str
    progress: str
    sources_queried: Optional[list] = None
    sources_found: Optional[list] = None
    social_quadrant: Optional[dict] = None
    unified_embedding: Optional[list] = None
    draft_message: Optional[str] = None
    social_hooks: Optional[list] = None
    result: Optional[dict] = None
    error: Optional[str] = None


@router.get("/interactions/detail/{job_id}", response_model=InteractionDetailResponse)
async def get_interaction_detail(job_id: str, db_session: Session = Depends(get_db)):
    """Get detailed results for a Phase 2b interaction workflow.
    
    Returns comprehensive results including:
    - Sources queried and found
    - Social quadrant mapping (4D profiling)
    - Unified embedding (triple-vector synthesis)
    - Enriched warm outreach with social hooks
    
    Args:
        job_id: Job ID from submit_interaction_v2b response
        
    Returns:
        Detailed interaction results
    """
    logger.info(f"Detail fetch for job_id={job_id}")
    
    try:
        job = db_session.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        metadata = json.loads(job.job_metadata or "{}")
        celery_task_id = metadata.get("celery_task_id")
        workflow_version = metadata.get("workflow_version", "2a")
        
        if not celery_task_id:
            return InteractionDetailResponse(
                job_id=job_id,
                task_id="",
                state="PENDING",
                workflow_version=workflow_version,
                progress="Queued...",
            )
        
        # Get detailed workflow result from Celery
        workflow_status = get_workflow_status(celery_task_id)
        result_data = workflow_status.get("meta", {})
        
        return InteractionDetailResponse(
            job_id=job_id,
            task_id=celery_task_id,
            state=workflow_status["state"],
            workflow_version=workflow_version,
            progress=workflow_status.get("progress", ""),
            sources_queried=result_data.get("sources_queried"),
            sources_found=result_data.get("sources_found"),
            social_quadrant=result_data.get("social_quadrant"),
            unified_embedding=result_data.get("unified_profile_embedding"),
            draft_message=result_data.get("draft_message"),
            social_hooks=result_data.get("social_hooks_used"),
            result=workflow_status.get("result"),
            error=workflow_status.get("error"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detail for job_id={job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get details: {e}")