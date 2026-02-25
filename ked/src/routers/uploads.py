"""Advanced audio upload endpoints with offline-first support.

Features:
1. Chunked uploads for large files
2. Resumable uploads (detect and resume)
3. Stream uploads to S3
4. Offline recording queue
5. Sync when connectivity returns
"""

import logging
import uuid
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .. import db
from ..auth import get_current_user
from ..exceptions import ValidationError, ExternalServiceError
from ..config import settings
from ..services.upload_handler import ChunkedUploadManager, StreamingUploadHandler, CompressionStrategy
from ..services.offline_manager import OfflineAudioManager, RecordingStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["uploads"])

# Initialize managers
chunked_upload_mgr = ChunkedUploadManager()
offline_mgr = OfflineAudioManager(user_storage_dir=settings.audio_storage_dir)


def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# Chunked Upload Endpoints
# ============================================================================

class InitChunkedUploadRequest(BaseModel):
    """Request to initiate chunked upload."""
    file_name: str = Field(..., min_length=1, max_length=500)
    file_size: int = Field(..., gt=0)
    mode: str = Field("recap", pattern="^(live|recap)$")


class InitChunkedUploadResponse(BaseModel):
    """Response with upload session details."""
    file_id: str
    upload_id: str
    chunk_size: int
    total_chunks: int
    chunk_hashes: dict = {}


@router.post("/chunked/init", response_model=InitChunkedUploadResponse, status_code=status.HTTP_201_CREATED)
def init_chunked_upload(
    request: InitChunkedUploadRequest,
    user_id: int = Depends(get_current_user),
):
    """Initialize a chunked upload session.
    
    For large files, client splits into chunks and uploads separately.
    Server tracks progress and can resume if interrupted.
    
    Args:
        request: Upload initialization request
        user_id: Extracted from JWT token
        
    Returns:
        Upload session info with chunk details
    """
    file_id = str(uuid.uuid4())
    upload_id = str(uuid.uuid4())
    
    try:
        session = chunked_upload_mgr.create_upload_session(
            user_id=user_id,
            file_id=file_id,
            file_size=request.file_size,
            file_name=request.file_name,
        )
        
        logger.info(
            f"[user_id={user_id}] Chunked upload initiated: file_id={file_id}, "
            f"chunks={session['total_chunks']}, chunk_size={session['chunk_size']}"
        )
        
        return InitChunkedUploadResponse(
            file_id=file_id,
            upload_id=upload_id,
            chunk_size=session["chunk_size"],
            total_chunks=session["total_chunks"],
        )
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to init chunked upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize upload")


class UploadChunkRequest(BaseModel):
    """Request to upload a single chunk."""
    chunk_number: int = Field(..., ge=0)
    total_chunks: int = Field(..., gt=0)


@router.post("/chunked/{file_id}/chunk", status_code=status.HTTP_200_OK)
async def upload_chunk(
    file_id: str,
    chunk: UploadFile,
    chunk_number: int = Query(..., ge=0),
    total_chunks: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user),
):
    """Upload a single chunk of a file.
    
    Chunks are reassembled server-side when all uploaded.
    
    Args:
        file_id: File ID from init step
        chunk: Chunk file data
        chunk_number: This chunk's number (0-indexed)
        total_chunks: Total number of chunks
        user_id: Extracted from JWT token
        
    Returns:
        Chunk upload status
    """
    try:
        chunk_data = await chunk.read()
        
        chunk_mgr = chunked_upload_mgr.save_chunk(
            file_id=file_id,
            chunk_number=chunk_number,
            chunk_data=chunk_data,
        )
        
        logger.info(
            f"[user_id={user_id}] Chunk uploaded: file_id={file_id}, "
            f"chunk={chunk_number}/{total_chunks}, size={len(chunk_data)}"
        )
        
        return {
            "file_id": file_id,
            "chunk_number": chunk_number,
            "chunk_hash": chunk_mgr["hash"],
            "chunk_size": chunk_mgr["size"],
            "progress": f"{chunk_number + 1}/{total_chunks}",
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Chunk upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload chunk")


class CompleteChunkedUploadRequest(BaseModel):
    """Request to complete chunked upload."""
    mode: str = Field("recap", pattern="^(live|recap)$")
    metadata: Optional[dict] = None


@router.post("/chunked/{file_id}/complete", status_code=status.HTTP_200_OK)
def complete_chunked_upload(
    file_id: str,
    request: CompleteChunkedUploadRequest,
    user_id: int = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Complete chunked upload and assemble file.
    
    Args:
        file_id: File ID
        request: Completion request with metadata
        user_id: Extracted from JWT token
        db_session: Database session
        
    Returns:
        Recording info with local storage path
    """
    try:
        # Assemble chunks into final file
        recording_id = str(uuid.uuid4())
        temp_path = f"/tmp/{recording_id}.wav"
        
        chunked_upload_mgr.complete_upload(file_id=file_id, output_path=temp_path)
        
        # Read assembled file
        with open(temp_path, "rb") as f:
            audio_data = f.read()
        
        # Save to local storage (persistent)
        recording_metadata = offline_mgr.save_recording(
            user_id=user_id,
            recording_id=recording_id,
            audio_data=audio_data,
            mode=request.mode,
            metadata=request.metadata,
        )
        
        logger.info(
            f"[user_id={user_id}] Chunked upload completed: recording_id={recording_id}, "
            f"size={len(audio_data)} bytes"
        )
        
        return {
            "recording_id": recording_id,
            "file_id": file_id,
            "size": len(audio_data),
            "status": "recorded",
            "mode": request.mode,
            "storage_path": f"/data/linkd/users/{user_id}/recordings/{recording_id}.wav",
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to complete chunked upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete upload")


# ============================================================================
# Resumable Upload Endpoints
# ============================================================================

@router.get("/chunked/{file_id}/status", status_code=status.HTTP_200_OK)
def get_upload_status(
    file_id: str,
    user_id: int = Depends(get_current_user),
):
    """Get status of chunked upload (for resuming).
    
    Useful for detecting which chunks need to be uploaded.
    
    Args:
        file_id: File ID
        user_id: Extracted from JWT token
        
    Returns:
        Upload status with uploaded chunks
    """
    session = chunked_upload_mgr.get_upload_session(file_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    if session["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this upload")
    
    return {
        "file_id": file_id,
        "file_name": session["file_name"],
        "file_size": session["file_size"],
        "total_chunks": session["total_chunks"],
        "uploaded_chunks": session.get("uploaded_chunks", []),
        "chunk_size": session["chunk_size"],
        "resumable": True,
    }


# ============================================================================
# Offline Recording Endpoints
# ============================================================================

class SaveOfflineRecordingRequest(BaseModel):
    """Request to save recording locally (offline)."""
    mode: str = Field("recap", pattern="^(live|recap)$")
    metadata: Optional[dict] = None


@router.post("/offline/save", status_code=status.HTTP_201_CREATED)
async def save_offline_recording(
    file: UploadFile,
    mode: str = Form("recap"),
    user_id: int = Depends(get_current_user),
):
    """Save recording locally without uploading.
    
    Useful for offline recording. File persists locally until synced.
    
    Args:
        file: Audio file
        mode: Recording mode
        user_id: Extracted from JWT token
        
    Returns:
        Recording saved confirmation
    """
    try:
        audio_data = await file.read()
        recording_id = str(uuid.uuid4())
        
        recording_metadata = offline_mgr.save_recording(
            user_id=user_id,
            recording_id=recording_id,
            audio_data=audio_data,
            mode=mode,
        )
        
        logger.info(
            f"[user_id={user_id}] Recording saved offline: recording_id={recording_id}, "
            f"size={len(audio_data)} bytes"
        )
        
        return {
            "recording_id": recording_id,
            "status": "recorded",
            "size": len(audio_data),
            "mode": mode,
            "storage_path": f"/data/linkd/users/{user_id}/recordings/{recording_id}.wav",
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to save offline recording: {e}")
        raise ExternalServiceError("Offline Storage", str(e))


@router.get("/offline/recordings")
def list_offline_recordings(
    user_id: int = Depends(get_current_user),
    status_filter: Optional[str] = None,
):
    """List recorded audio files stored locally.
    
    Args:
        user_id: Extracted from JWT token
        status_filter: Optional filter (recorded, uploading, uploaded, processing, completed)
        
    Returns:
        List of recordings
    """
    try:
        recordings = offline_mgr.list_recordings(
            user_id=user_id,
            status_filter=status_filter,
        )
        
        logger.info(f"[user_id={user_id}] Listed {len(recordings)} offline recordings")
        
        return {
            "count": len(recordings),
            "recordings": recordings,
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to list recordings: {e}")
        raise HTTPException(status_code=500, detail="Failed to list recordings")


@router.get("/offline/queue")
def get_offline_queue(
    user_id: int = Depends(get_current_user),
):
    """Get upload queue for offline recordings.
    
    Returns recordings that are queued for upload when online.
    
    Args:
        user_id: Extracted from JWT token
        
    Returns:
        Queued recordings
    """
    try:
        queue = offline_mgr.get_upload_queue(user_id)
        
        logger.info(f"[user_id={user_id}] Retrieved upload queue: {len(queue)} items")
        
        return {
            "queue_count": len(queue),
            "queue": queue,
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to get queue: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue")


@router.post("/offline/sync")
def sync_offline_queue(
    user_id: int = Depends(get_current_user),
):
    """Sync offline queue when connectivity returns.
    
    Client calls this when network is available.
    Returns list of recordings ready to upload.
    
    Args:
        user_id: Extracted from JWT token
        
    Returns:
        Recordings ready to sync
    """
    try:
        queue = offline_mgr.get_upload_queue(user_id)
        
        # For each queued item, provide presigned upload URL or streaming endpoint
        ready_to_sync = []
        for item in queue:
            recording_metadata = offline_mgr.get_recording_metadata(
                user_id,
                item["recording_id"],
            )
            if recording_metadata:
                ready_to_sync.append({
                    "recording_id": item["recording_id"],
                    "file_size": recording_metadata["file_size"],
                    "mode": recording_metadata["mode"],
                    "queued_at": item["queued_at"],
                    "upload_url": f"/upload/sync/{item['recording_id']}",
                })
        
        logger.info(f"[user_id={user_id}] Sync initiated: {len(ready_to_sync)} recordings ready")
        
        return {
            "ready_to_sync": len(ready_to_sync),
            "queue": ready_to_sync,
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Sync failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync queue")


@router.post("/sync/{recording_id}")
def sync_single_recording(
    recording_id: str,
    user_id: int = Depends(get_current_user),
):
    """Upload a single offline recording when online.
    
    Args:
        recording_id: Recording ID to upload
        user_id: Extracted from JWT token
        
    Returns:
        Upload initiated confirmation
    """
    try:
        # Queue for upload
        offline_mgr.queue_for_upload(user_id, recording_id)
        
        logger.info(f"[user_id={user_id}] Recording queued for sync: {recording_id}")
        
        return {
            "recording_id": recording_id,
            "status": "uploading",
            "message": "Recording queued for upload. Check status with /upload/offline/queue",
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to queue for sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue for sync")


@router.get("/offline/storage-stats")
def get_storage_stats(
    user_id: int = Depends(get_current_user),
):
    """Get local storage statistics.
    
    Args:
        user_id: Extracted from JWT token
        
    Returns:
        Storage stats
    """
    try:
        stats = offline_mgr.get_storage_stats(user_id)
        
        return {
            "total_size_mb": round(stats["total_size_mb"], 2),
            "total_recordings": stats["total_recordings"],
            "by_status": stats["by_status"],
        }
    except Exception as e:
        logger.error(f"[user_id={user_id}] Failed to get storage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get storage stats")


# ============================================================================
# Compression & Optimization Endpoints
# ============================================================================

@router.post("/analyze/{recording_id}")
def analyze_recording(
    recording_id: str,
    user_id: int = Depends(get_current_user),
):
    """Analyze recording for optimization opportunities.
    
    Suggests compression if beneficial.
    
    Args:
        recording_id: Recording ID to analyze
        user_id: Extracted from JWT token
        
    Returns:
        Analysis and recommendations
    """
    try:
        metadata = offline_mgr.get_recording_metadata(user_id, recording_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        file_size = metadata["file_size"]
        should_compress = CompressionStrategy.should_compress(file_size, "audio/wav")
        recommended_format = (
            CompressionStrategy.suggest_compression_format("audio/wav")
            if should_compress
            else None
        )
        
        return {
            "recording_id": recording_id,
            "file_size": file_size,
            "should_compress": should_compress,
            "recommended_format": recommended_format,
            "estimated_compressed_size": (
                int(file_size * 0.3)  # Rough estimate
                if should_compress
                else file_size
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_id={user_id}] Analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze recording")
