"""Local storage service for offline-first audio recording support.

Manages:
1. Local audio file persistence
2. Pending upload queue (for when offline)
3. Offline recording buffer
4. Sync when connectivity returns
"""

import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class RecordingStatus(str, Enum):
    """Status of a recording."""
    RECORDED = "recorded"  # Saved locally
    UPLOADING = "uploading"  # Currently uploading
    UPLOADED = "uploaded"  # Uploaded to server
    PROCESSING = "processing"  # Being processed by server
    COMPLETED = "completed"  # Processing complete
    FAILED = "failed"  # Upload/processing failed


class OfflineAudioManager:
    """Manages offline-first audio recording with local persistence."""
    
    def __init__(self, user_storage_dir: str = "/data/linkd/users"):
        """Initialize offline audio manager.
        
        Args:
            user_storage_dir: Base directory for user data (e.g., /data/linkd/users/{user_id})
        """
        self.base_storage_dir = user_storage_dir
        logger.info(f"OfflineAudioManager initialized with base_dir={user_storage_dir}")
    
    def _get_user_dir(self, user_id: int) -> Path:
        """Get user's storage directory.
        
        Args:
            user_id: User ID
            
        Returns:
            Path to user directory
        """
        user_dir = Path(self.base_storage_dir) / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def _get_recordings_dir(self, user_id: int) -> Path:
        """Get user's recordings directory.
        
        Args:
            user_id: User ID
            
        Returns:
            Path to recordings directory
        """
        recordings_dir = self._get_user_dir(user_id) / "recordings"
        recordings_dir.mkdir(parents=True, exist_ok=True)
        return recordings_dir
    
    def _get_queue_dir(self, user_id: int) -> Path:
        """Get user's upload queue directory.
        
        Args:
            user_id: User ID
            
        Returns:
            Path to queue directory
        """
        queue_dir = self._get_user_dir(user_id) / "queue"
        queue_dir.mkdir(parents=True, exist_ok=True)
        return queue_dir
    
    def save_recording(
        self,
        user_id: int,
        recording_id: str,
        audio_data: bytes,
        mode: str = "recap",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Save a recording locally.
        
        Stores audio file and metadata for later upload.
        This allows offline recording - upload happens when online.
        
        Args:
            user_id: User ID
            recording_id: Unique recording ID (UUID)
            audio_data: Raw audio bytes
            mode: Recording mode ("live" or "recap")
            metadata: Optional metadata dict
            
        Returns:
            Recording metadata
        """
        recordings_dir = self._get_recordings_dir(user_id)
        audio_file = recordings_dir / f"{recording_id}.wav"
        metadata_file = recordings_dir / f"{recording_id}.json"
        
        # Save audio file
        with open(audio_file, "wb") as f:
            f.write(audio_data)
        
        # Save metadata
        record_metadata = {
            "recording_id": recording_id,
            "user_id": user_id,
            "mode": mode,
            "status": RecordingStatus.RECORDED.value,
            "file_size": len(audio_data),
            "created_at": datetime.utcnow().isoformat(),
            "uploaded_at": None,
            "processing_job_id": None,
            "custom_metadata": metadata or {},
        }
        
        with open(metadata_file, "w") as f:
            json.dump(record_metadata, f, indent=2)
        
        logger.info(
            f"Recording saved locally: user_id={user_id}, recording_id={recording_id}, "
            f"size={len(audio_data)} bytes"
        )
        
        return record_metadata
    
    def get_recording(self, user_id: int, recording_id: str) -> Optional[bytes]:
        """Retrieve a recording from local storage.
        
        Args:
            user_id: User ID
            recording_id: Recording ID
            
        Returns:
            Audio bytes or None if not found
        """
        recordings_dir = self._get_recordings_dir(user_id)
        audio_file = recordings_dir / f"{recording_id}.wav"
        
        if not audio_file.exists():
            logger.warning(f"Recording not found: {recording_id}")
            return None
        
        with open(audio_file, "rb") as f:
            return f.read()
    
    def get_recording_metadata(self, user_id: int, recording_id: str) -> Optional[Dict]:
        """Get recording metadata.
        
        Args:
            user_id: User ID
            recording_id: Recording ID
            
        Returns:
            Metadata dict or None if not found
        """
        recordings_dir = self._get_recordings_dir(user_id)
        metadata_file = recordings_dir / f"{recording_id}.json"
        
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, "r") as f:
            return json.load(f)
    
    def list_recordings(
        self,
        user_id: int,
        status_filter: Optional[str] = None,
    ) -> List[Dict]:
        """List user's recordings.
        
        Args:
            user_id: User ID
            status_filter: Optional status filter (e.g., "recorded", "processing")
            
        Returns:
            List of recording metadata
        """
        recordings_dir = self._get_recordings_dir(user_id)
        recordings = []
        
        for metadata_file in recordings_dir.glob("*.json"):
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            
            if status_filter is None or metadata["status"] == status_filter:
                recordings.append(metadata)
        
        return sorted(recordings, key=lambda x: x["created_at"], reverse=True)
    
    def queue_for_upload(
        self,
        user_id: int,
        recording_id: str,
    ) -> Dict:
        """Queue a recording for upload.
        
        Args:
            user_id: User ID
            recording_id: Recording ID
            
        Returns:
            Queue item metadata
        """
        queue_dir = self._get_queue_dir(user_id)
        queue_item_file = queue_dir / f"{recording_id}.json"
        
        queue_item = {
            "recording_id": recording_id,
            "user_id": user_id,
            "queued_at": datetime.utcnow().isoformat(),
            "retry_count": 0,
            "last_error": None,
        }
        
        with open(queue_item_file, "w") as f:
            json.dump(queue_item, f, indent=2)
        
        # Update recording status
        self._update_recording_status(user_id, recording_id, RecordingStatus.UPLOADING)
        
        logger.info(f"Recording queued for upload: {recording_id}")
        return queue_item
    
    def get_upload_queue(self, user_id: int) -> List[Dict]:
        """Get upload queue for user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of queued items
        """
        queue_dir = self._get_queue_dir(user_id)
        queue_items = []
        
        if not queue_dir.exists():
            return []
        
        for item_file in queue_dir.glob("*.json"):
            with open(item_file, "r") as f:
                queue_items.append(json.load(f))
        
        return sorted(queue_items, key=lambda x: x["queued_at"])
    
    def remove_from_queue(self, user_id: int, recording_id: str) -> None:
        """Remove item from upload queue.
        
        Args:
            user_id: User ID
            recording_id: Recording ID
        """
        queue_dir = self._get_queue_dir(user_id)
        queue_item_file = queue_dir / f"{recording_id}.json"
        
        if queue_item_file.exists():
            queue_item_file.unlink()
            logger.info(f"Removed from queue: {recording_id}")
    
    def _update_recording_status(
        self,
        user_id: int,
        recording_id: str,
        status: RecordingStatus,
        job_id: Optional[str] = None,
    ) -> None:
        """Update recording status.
        
        Args:
            user_id: User ID
            recording_id: Recording ID
            status: New status
            job_id: Optional job ID for processing
        """
        recordings_dir = self._get_recordings_dir(user_id)
        metadata_file = recordings_dir / f"{recording_id}.json"
        
        if not metadata_file.exists():
            return
        
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        metadata["status"] = status.value
        if job_id:
            metadata["processing_job_id"] = job_id
        
        # Update timestamp based on status
        if status == RecordingStatus.UPLOADED:
            metadata["uploaded_at"] = datetime.utcnow().isoformat()
        
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def mark_uploaded(self, user_id: int, recording_id: str) -> None:
        """Mark recording as uploaded.
        
        Args:
            user_id: User ID
            recording_id: Recording ID
        """
        self._update_recording_status(user_id, recording_id, RecordingStatus.UPLOADED)
        self.remove_from_queue(user_id, recording_id)
    
    def mark_processing(self, user_id: int, recording_id: str, job_id: str) -> None:
        """Mark recording as being processed.
        
        Args:
            user_id: User ID
            recording_id: Recording ID
            job_id: Server job ID
        """
        self._update_recording_status(
            user_id,
            recording_id,
            RecordingStatus.PROCESSING,
            job_id=job_id,
        )
    
    def cleanup_old_failed(self, user_id: int, days: int = 7) -> int:
        """Clean up failed recordings older than specified days.
        
        Args:
            user_id: User ID
            days: Age threshold in days
            
        Returns:
            Number of recordings deleted
        """
        recordings_dir = self._get_recordings_dir(user_id)
        deleted_count = 0
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        for metadata_file in recordings_dir.glob("*.json"):
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            
            if metadata["status"] == RecordingStatus.FAILED.value:
                created_at = datetime.fromisoformat(metadata["created_at"])
                
                if created_at < cutoff_date:
                    # Delete metadata and audio file
                    recording_id = metadata["recording_id"]
                    audio_file = recordings_dir / f"{recording_id}.wav"
                    
                    metadata_file.unlink()
                    if audio_file.exists():
                        audio_file.unlink()
                    
                    deleted_count += 1
                    logger.info(f"Deleted old failed recording: {recording_id}")
        
        return deleted_count
    
    def get_storage_stats(self, user_id: int) -> Dict:
        """Get storage statistics for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Storage stats
        """
        recordings_dir = self._get_recordings_dir(user_id)
        
        total_size = 0
        total_recordings = 0
        by_status = {}
        
        for metadata_file in recordings_dir.glob("*.json"):
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            
            total_recordings += 1
            total_size += metadata.get("file_size", 0)
            
            status = metadata["status"]
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_size_mb": total_size / (1024 * 1024),
            "total_recordings": total_recordings,
            "by_status": by_status,
        }
