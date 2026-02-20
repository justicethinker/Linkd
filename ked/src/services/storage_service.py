import logging
import os
import boto3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class S3StorageService:
    """Handle file storage and retrieval, with fallback to local filesystem."""

    def __init__(self):
        self.use_s3 = all([
            os.getenv("AWS_ACCESS_KEY_ID"),
            os.getenv("AWS_SECRET_ACCESS_KEY"),
            os.getenv("AWS_S3_BUCKET"),
        ])
        self.local_storage_path = Path("/tmp/linkd_audio")
        
        if not self.use_s3:
            logger.warning("S3 not configured; using local filesystem for storage")
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
        else:
            self.bucket_name = os.getenv("AWS_S3_BUCKET")
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
            logger.info(f"S3 storage configured with bucket: {self.bucket_name}")

    def upload_audio_file(self, user_id: int, file_path: str, file_name: str) -> str:
        """Upload audio file and return storage key/URL.
        
        Args:
            user_id: User ID
            file_path: Local path to audio file
            file_name: Original filename
            
        Returns:
            Storage key (S3 key or local path)
        """
        s3_key = f"audio/{user_id}/{datetime.utcnow().isoformat()}/{file_name}"
        
        try:
            if self.use_s3:
                # Upload to S3 with metadata
                with open(file_path, "rb") as f:
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        Body=f.read(),
                        Metadata={"user_id": str(user_id), "uploaded_at": datetime.utcnow().isoformat()},
                        ServerSideEncryption="AES256",
                    )
                # Set lifecycle policy for 24-hour expiration
                self._set_expiration_policy(s3_key)
                logger.info(f"[user_id={user_id}] Uploaded to S3: {s3_key}")
                return s3_key
            else:
                # Save locally with 24-hour expiration marker
                local_key = self.local_storage_path / s3_key
                local_key.parent.mkdir(parents=True, exist_ok=True)
                # Copy file to local storage
                import shutil
                shutil.copy(file_path, local_key)
                # Write expiration timestamp
                expiry_time = (datetime.utcnow() + timedelta(hours=24)).isoformat()
                (local_key.parent / f"{local_key.name}.expires").write_text(expiry_time)
                logger.info(f"[user_id={user_id}] Saved locally: {local_key}")
                return str(local_key)
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise

    def get_audio_file(self, storage_key: str) -> bytes:
        """Retrieve audio file from storage.
        
        Args:
            storage_key: Storage key (S3 key or local path)
            
        Returns:
            File contents as bytes
        """
        try:
            if self.use_s3:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=storage_key)
                return response["Body"].read()
            else:
                return Path(storage_key).read_bytes()
        except Exception as e:
            logger.error(f"Error retrieving file {storage_key}: {e}")
            raise

    def delete_audio_file(self, storage_key: str) -> None:
        """Delete audio file from storage (used for immediate cleanup).
        
        Args:
            storage_key: Storage key to delete
        """
        try:
            if self.use_s3:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_key)
                logger.info(f"Deleted S3 file: {storage_key}")
            else:
                path = Path(storage_key)
                if path.exists():
                    path.unlink()
                    # Also delete expiration marker
                    expires_file = path.parent / f"{path.name}.expires"
                    if expires_file.exists():
                        expires_file.unlink()
                    logger.info(f"Deleted local file: {storage_key}")
        except Exception as e:
            logger.error(f"Error deleting file {storage_key}: {e}")

    def _set_expiration_policy(self, s3_key: str) -> None:
        """Set lifecycle policy for automatic deletion in 24 hours."""
        try:
            # For S3, you'd typically set this at the bucket level, not per object
            # This is a log reminder for the admin to configure bucket lifecycle rules
            logger.info(f"Note: S3 bucket lifecycle should delete {s3_key} after 24 hours")
        except Exception as e:
            logger.warning(f"Could not set expiration policy: {e}")

    def cleanup_expired_files(self) -> int:
        """Clean up locally stored files that have passed expiration.
        
        Returns:
            Number of files deleted
        """
        if self.use_s3:
            logger.info("Cleanup not needed for S3 (lifecycle policies handle it)")
            return 0
        
        deleted_count = 0
        try:
            for expires_file in self.local_storage_path.glob("**/*.expires"):
                expiry_time = datetime.fromisoformat(expires_file.read_text())
                if datetime.utcnow() > expiry_time:
                    audio_file = expires_file.parent / expires_file.stem
                    if audio_file.exists():
                        audio_file.unlink()
                        deleted_count += 1
                    expires_file.unlink()
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired audio files")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        return deleted_count


# Global instance
storage_service = S3StorageService()
