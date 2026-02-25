"""Protected ingest endpoint for audio data ingestion and processing.

Features:
1. JWT authentication via Supabase
2. Audio file upload to Supabase storage
3. Database record creation for tracking
4. Async task queuing for processing
"""

import logging
import uuid
import asyncio
import tempfile
import subprocess
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, Field

from ..supabase_client import (
    get_current_user,
    get_current_user_data,
    get_supabase_storage,
    get_supabase_database,
    SupabaseStorage,
    SupabaseDatabase,
)
from ..exceptions import ValidationError, ExternalServiceError
from ..config import settings
from ..tasks.transcription_tasks import transcribe_audio_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


# ============================================================================
# Request/Response Models
# ============================================================================

class IngestRequest(BaseModel):
    """Request to ingest audio data."""
    mode: str = Field("recap", pattern="^(live|recap)$")
    duration_seconds: int = Field(..., gt=0, le=3600)  # Max 1 hour
    metadata: Optional[dict] = Field(None, max_items=20)  # Optional metadata


class IngestResponse(BaseModel):
    """Response from ingest operation."""
    success: bool
    recording_id: str
    user_id: str
    storage_url: Optional[str] = None
    job_id: Optional[str] = None
    message: str


# ============================================================================
# Protected Ingest Endpoints
# ============================================================================

@router.post(
    "/audio",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest audio data",
    description="Upload and process audio data. Requires Supabase JWT authentication.",
)
async def ingest_audio(
    file: UploadFile = File(..., description="Audio file (WAV, MP3, OGG)"),
    mode: str = Form("recap"),
    duration_seconds: int = Form(...),
    metadata: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user),
    storage: SupabaseStorage = Depends(get_supabase_storage),
    db: SupabaseDatabase = Depends(get_supabase_database),
) -> IngestResponse:
    """Ingest audio data with Supabase authentication.
    
    **Authentication**: Required. Bearer token from Supabase auth.
    
    **Parameters**:
    - **file**: Audio file (WAV, MP3, OGG format)
    - **mode**: Type of recording (live or recap)
    - **duration_seconds**: Recording duration in seconds (max 3600)
    - **metadata**: Optional JSON metadata
    
    **Returns**: Recording ID and storage URL
    
    **Example**:
    ```bash
    curl -X POST http://localhost:8000/ingest/audio \\
      -H "Authorization: Bearer $TOKEN" \\
      -F "file=@recording.wav" \\
      -F "mode=recap" \\
      -F "duration_seconds=120"
    ```
    """
    try:
        # Validate file type (allow common compressed formats too)
        allowed_formats = {"audio/wav", "audio/mpeg", "audio/ogg", "audio/x-m4a", "audio/mp4", "audio/opus"}
        if file.content_type not in allowed_formats:
            raise ValidationError(
                f"Invalid audio format: {file.content_type}. Supported: {allowed_formats}"
            )

        # Validate mode
        if mode not in ("live", "recap"):
            raise ValidationError(f"Invalid mode: {mode}. Must be 'live' or 'recap'")

        # Validate duration
        if duration_seconds <= 0 or duration_seconds > 3600:
            raise ValidationError(f"Invalid duration: {duration_seconds}. Must be 1-3600 seconds")

        # Save incoming stream to a temporary file for preprocessing
        input_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".upload")
        try:
            # Stream write to avoid loading entire raw upload in memory
            while True:
                chunk = await file.read(1024 * 64)
                if not chunk:
                    break
                input_tmp.write(chunk)
            input_tmp.flush()
            input_tmp.close()

            # Preprocess: convert to m4a (AAC), mono, 16kHz, 32kbps (mobile-friendly)
            output_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".m4a")
            output_tmp.close()

            ffmpeg_cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-i", input_tmp.name,
                "-ac", "1",
                "-ar", "16000",
                "-b:a", "32k",
                "-c:a", "aac",
                output_tmp.name,
            ]

            try:
                subprocess.run(ffmpeg_cmd, check=True, timeout=60)
                with open(output_tmp.name, "rb") as fh:
                    processed_bytes = fh.read()
                processed_content_type = "audio/mp4"
                processed_ext = "m4a"
            except Exception:
                # If preprocessing fails, fall back to raw uploaded bytes
                with open(input_tmp.name, "rb") as fh:
                    processed_bytes = fh.read()
                processed_content_type = file.content_type
                processed_ext = file.filename.split('.')[-1] if file.filename else 'wav'

            file_size = len(processed_bytes)
            max_size = settings.max_upload_size_mb * 1024 * 1024
            if file_size > max_size:
                raise ValidationError(f"File too large after preprocessing: {file_size / 1024 / 1024:.1f}MB. Maximum: {settings.max_upload_size_mb}MB")

            # Generate IDs early
            recording_id = str(uuid.uuid4())
            job_id = str(uuid.uuid4())

            logger.info(f"[{user_id}] Ingesting audio: {recording_id} ({file_size} bytes, {mode}) - job={job_id}")

            # Create initial DB record with processing state
            recording_data = {
                "user_id": user_id,
                "recording_id": recording_id,
                "mode": mode,
                "duration_seconds": duration_seconds,
                "file_size": file_size,
                "storage_url": None,
                "status": "processing",
                "metadata": metadata,
                "job_id": job_id,
            }
            await db.insert("recordings", recording_data)

            # Branch B: Dispatch Celery transcription immediately with bytes (no wait)
            try:
                transcribe_audio_bytes.delay(user_id, job_id, processed_bytes, mode)
                logger.info(f"[{user_id}] Dispatched transcription task (job={job_id})")
            except Exception as e:
                logger.warning(f"Failed to dispatch transcription task: {e}")

            # Branch A: Upload to Supabase storage in background (storage path must start with user_id)
            storage_path = f"{user_id}/recordings/{recording_id}.{processed_ext}"

            async def _upload_and_update():
                try:
                    # upload to the `interactions` bucket (source-of-truth for audio)
                    url = await storage.upload_file(bucket="interactions", path=storage_path, file_data=processed_bytes, content_type=processed_content_type)
                    # Update recordings row with storage_url and mark uploaded
                    try:
                        db.client.table("recordings").update({"storage_url": url, "status": "uploaded"}).eq("recording_id", recording_id).eq("user_id", user_id).execute()
                        logger.info(f"[{user_id}] Storage upload complete and DB updated: {url}")
                    except Exception as e:
                        logger.warning(f"Failed to update recordings row after upload: {e}")
                except Exception as e:
                    logger.error(f"[{user_id}] Background upload failed: {e}")

            asyncio.create_task(_upload_and_update())

            return IngestResponse(success=True, recording_id=recording_id, user_id=user_id, storage_url=None, job_id=job_id, message="Ingest started (uploading + transcription dispatched)")
        finally:
            # Cleanup temp files
            try:
                if os.path.exists(input_tmp.name):
                    os.unlink(input_tmp.name)
            except Exception:
                pass
            try:
                if 'output_tmp' in locals() and os.path.exists(output_tmp.name):
                    os.unlink(output_tmp.name)
            except Exception:
                pass
    
    except ValidationError as e:
        logger.warning(f"[{user_id}] Validation error: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    
    except Exception as e:
        logger.error(f"[{user_id}] Ingest failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest audio",
        )


@router.get(
    "/recording/{recording_id}",
    response_model=dict,
    summary="Get recording details",
    description="Retrieve details about an ingested recording.",
)
async def get_recording(
    recording_id: str,
    user_id: str = Depends(get_current_user),
    db: SupabaseDatabase = Depends(get_supabase_database),
):
    """Get recording details.
    
    **Authentication**: Required. Bearer token from Supabase auth.
    
    **Returns**: Recording metadata and storage information
    """
    try:
        # Query database for recording
        records = await db.query(
            "recordings",
            recording_id=recording_id,
            user_id=user_id,
        )
        
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found",
            )
        
        logger.info(f"[{user_id}] Retrieved recording: {recording_id}")
        
        return {
            "success": True,
            "data": records[0],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{user_id}] Failed to get recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recording",
        )


@router.get(
    "/recordings",
    response_model=dict,
    summary="List user recordings",
    description="List all recordings for the authenticated user.",
)
async def list_recordings(
    status_filter: Optional[str] = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user),
    db: SupabaseDatabase = Depends(get_supabase_database),
):
    """List user's recordings.
    
    **Authentication**: Required. Bearer token from Supabase auth.
    
    **Query Parameters**:
    - **status_filter**: Filter by status (uploaded, processing, completed, failed)
    - **limit**: Maximum number of results (1-100, default 50)
    
    **Returns**: List of user's recordings
    """
    try:
        if limit < 1 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100")
        
        # Query database for user's recordings
        query_filters = {"user_id": user_id}
        if status_filter:
            query_filters["status"] = status_filter
        
        records = await db.query("recordings", **query_filters)
        
        logger.info(f"[{user_id}] Retrieved {len(records)} recordings")
        
        return {
            "success": True,
            "count": len(records),
            "data": records[:limit],
        }
    
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"[{user_id}] Failed to list recordings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list recordings",
        )


@router.delete(
    "/recording/{recording_id}",
    response_model=dict,
    summary="Delete recording",
    description="Delete a recording and its storage.",
)
async def delete_recording(
    recording_id: str,
    user_id: str = Depends(get_current_user),
    storage: SupabaseStorage = Depends(get_supabase_storage),
    db: SupabaseDatabase = Depends(get_supabase_database),
):
    """Delete a recording.
    
    **Authentication**: Required. Bearer token from Supabase auth.
    
    **Returns**: Confirmation of deletion
    """
    try:
        # Query database to verify ownership
        records = await db.query(
            "recordings",
            recording_id=recording_id,
            user_id=user_id,
        )
        
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found",
            )
        
        record = records[0]
        
        # Delete from storage
        if record.get("storage_url"):
            storage_path = record["storage_url"].split("/")[-1]
            await storage.delete_file(bucket="recordings", path=storage_path)
        
        # Delete from database
        db.client.table("recordings").delete().eq(
            "recording_id", recording_id
        ).eq("user_id", user_id).execute()
        
        logger.info(f"[{user_id}] Deleted recording: {recording_id}")
        
        return {
            "success": True,
            "message": "Recording deleted successfully",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{user_id}] Failed to delete recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete recording",
        )


@router.get(
    "/status",
    response_model=dict,
    summary="Ingest service status",
    description="Check if ingest service is ready.",
)
async def ingest_status():
    """Get ingest service status.
    
    **No authentication required** - Health check endpoint.
    
    **Returns**: Service status and configuration
    """
    try:
        return {
            "success": True,
            "service": "ingest",
            "status": "ready",
            "max_upload_size_mb": settings.max_upload_size_mb,
            "supported_formats": ["wav", "mp3", "ogg"],
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "success": False,
            "service": "ingest",
            "status": "error",
            "error": str(e),
        }
