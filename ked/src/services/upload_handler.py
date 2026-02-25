"""Large file upload handler with multiple strategies.

Supports:
1. Chunked uploads (split files into chunks)
2. Resumable uploads (detect and resume failed uploads)
3. Streaming uploads (stream to S3 without loading into memory)
4. Client-side compression detection
5. Multipart uploads with progress tracking
"""

import logging
import hashlib
import os
from dataclasses import dataclass
from typing import BinaryIO, Optional, Dict, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UploadChunk:
    """Represents a single chunk in a multipart upload."""
    chunk_number: int
    total_chunks: int
    data: bytes
    chunk_size: int
    md5_hash: str
    
    def calculate_hash(self) -> str:
        """Calculate MD5 hash of chunk data."""
        return hashlib.md5(self.data).hexdigest()


class ChunkedUploadManager:
    """Manages chunked uploads for large files."""
    
    # Default chunk size: 5MB (AWS S3 minimum for multipart)
    DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024
    
    def __init__(self, cache_dir: str = "/tmp/linkd_uploads"):
        """Initialize upload manager.
        
        Args:
            cache_dir: Directory to store upload metadata
        """
        self.cache_dir = cache_dir
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"ChunkedUploadManager initialized with cache_dir={cache_dir}")
    
    def get_chunk_size(self, file_size: int) -> int:
        """Determine optimal chunk size based on file size.
        
        Strategy:
        - Files < 25MB: 1MB chunks
        - Files 25-100MB: 5MB chunks  
        - Files > 100MB: 10MB chunks
        
        Args:
            file_size: Total file size in bytes
            
        Returns:
            Optimal chunk size in bytes
        """
        if file_size < 25 * 1024 * 1024:
            return 1 * 1024 * 1024  # 1MB
        elif file_size < 100 * 1024 * 1024:
            return 5 * 1024 * 1024  # 5MB
        else:
            return 10 * 1024 * 1024  # 10MB
    
    def create_upload_session(
        self,
        user_id: int,
        file_id: str,
        file_size: int,
        file_name: str,
    ) -> Dict:
        """Create a new upload session.
        
        Args:
            user_id: User ID
            file_id: Unique file ID (UUID)
            file_size: Total file size
            file_name: Original file name
            
        Returns:
            Upload session metadata
        """
        chunk_size = self.get_chunk_size(file_size)
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        session = {
            "file_id": file_id,
            "user_id": user_id,
            "file_name": file_name,
            "file_size": file_size,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "uploaded_chunks": [],
            "chunk_hashes": {},
        }
        
        session_file = os.path.join(self.cache_dir, f"{file_id}.json")
        import json
        with open(session_file, "w") as f:
            json.dump(session, f)
        
        logger.info(
            f"Upload session created: file_id={file_id}, "
            f"total_chunks={total_chunks}, chunk_size={chunk_size}"
        )
        return session
    
    def get_upload_session(self, file_id: str) -> Optional[Dict]:
        """Retrieve existing upload session.
        
        Args:
            file_id: File ID to retrieve
            
        Returns:
            Session metadata or None if not found
        """
        session_file = os.path.join(self.cache_dir, f"{file_id}.json")
        if not os.path.exists(session_file):
            return None
        
        import json
        with open(session_file, "r") as f:
            return json.load(f)
    
    def save_chunk(
        self,
        file_id: str,
        chunk_number: int,
        chunk_data: bytes,
    ) -> Dict:
        """Save an uploaded chunk.
        
        Args:
            file_id: File ID
            chunk_number: Chunk number (0-indexed)
            chunk_data: Chunk data bytes
            
        Returns:
            Chunk metadata
        """
        chunk_hash = hashlib.md5(chunk_data).hexdigest()
        chunk_file = os.path.join(self.cache_dir, f"{file_id}_chunk_{chunk_number}")
        
        with open(chunk_file, "wb") as f:
            f.write(chunk_data)
        
        logger.debug(f"Chunk saved: file_id={file_id}, chunk={chunk_number}, hash={chunk_hash}")
        
        return {
            "chunk_number": chunk_number,
            "hash": chunk_hash,
            "size": len(chunk_data),
        }
    
    def complete_upload(self, file_id: str, output_path: str) -> str:
        """Assemble chunks into final file.
        
        Args:
            file_id: File ID
            output_path: Path to write assembled file
            
        Returns:
            Path to assembled file
        """
        session = self.get_upload_session(file_id)
        if not session:
            raise ValueError(f"No upload session found for {file_id}")
        
        total_chunks = session["total_chunks"]
        
        # Assemble file from chunks
        with open(output_path, "wb") as output_file:
            for chunk_num in range(total_chunks):
                chunk_file = os.path.join(self.cache_dir, f"{file_id}_chunk_{chunk_num}")
                if not os.path.exists(chunk_file):
                    raise ValueError(f"Missing chunk {chunk_num} for file {file_id}")
                
                with open(chunk_file, "rb") as chunk_f:
                    output_file.write(chunk_f.read())
        
        # Cleanup session and chunks
        self._cleanup_upload(file_id)
        
        logger.info(f"Upload completed: file_id={file_id}, output={output_path}")
        return output_path
    
    def _cleanup_upload(self, file_id: str) -> None:
        """Clean up upload session and chunks.
        
        Args:
            file_id: File ID to clean up
        """
        session_file = os.path.join(self.cache_dir, f"{file_id}.json")
        if os.path.exists(session_file):
            os.remove(session_file)
        
        # Remove all chunks
        import glob
        for chunk_file in glob.glob(os.path.join(self.cache_dir, f"{file_id}_chunk_*")):
            try:
                os.remove(chunk_file)
            except Exception as e:
                logger.warning(f"Failed to remove chunk file {chunk_file}: {e}")


class StreamingUploadHandler:
    """Handle streaming uploads directly to S3."""
    
    def __init__(self, s3_client=None):
        """Initialize streaming handler.
        
        Args:
            s3_client: Boto3 S3 client
        """
        self.s3_client = s3_client
    
    def stream_to_s3(
        self,
        file_obj: BinaryIO,
        bucket: str,
        key: str,
        content_type: str = "audio/wav",
        progress_callback: Optional[Callable] = None,
    ) -> Dict:
        """Stream file directly to S3 using multipart upload.
        
        Args:
            file_obj: File object to stream
            bucket: S3 bucket name
            key: S3 object key
            content_type: MIME type
            progress_callback: Optional callback for progress (bytes_uploaded)
            
        Returns:
            Upload result metadata
        """
        if not self.s3_client:
            raise ValueError("S3 client not configured")
        
        try:
            # Create multipart upload
            mpu = self.s3_client.create_multipart_upload(
                Bucket=bucket,
                Key=key,
                ContentType=content_type,
            )
            upload_id = mpu["UploadId"]
            
            # Upload parts
            parts = []
            part_number = 1
            chunk_size = 5 * 1024 * 1024  # 5MB parts
            bytes_uploaded = 0
            
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                
                part = self.s3_client.upload_part(
                    Bucket=bucket,
                    Key=key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=chunk,
                )
                
                parts.append({
                    "PartNumber": part_number,
                    "ETag": part["ETag"],
                })
                
                bytes_uploaded += len(chunk)
                if progress_callback:
                    progress_callback(bytes_uploaded)
                
                part_number += 1
                logger.debug(f"Uploaded part {part_number-1}, total: {bytes_uploaded} bytes")
            
            # Complete multipart upload
            response = self.s3_client.complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            
            logger.info(f"Stream completed: {key}, bytes={bytes_uploaded}, parts={len(parts)}")
            return {
                "key": key,
                "location": response.get("Location"),
                "bytes_uploaded": bytes_uploaded,
                "part_count": len(parts),
            }
        except Exception as e:
            logger.error(f"Stream to S3 failed: {e}")
            raise


class CompressionStrategy:
    """Detect and suggest compression strategies."""
    
    @staticmethod
    def should_compress(file_size: int, file_type: str) -> bool:
        """Determine if file should be compressed.
        
        Strategy:
        - Audio files > 50MB: compress
        - Already compressed formats: skip (mp3, opus, aac)
        
        Args:
            file_size: File size in bytes
            file_type: MIME type or extension
            
        Returns:
            Whether to compress
        """
        no_compress = {"audio/mp3", "audio/mpeg", "audio/opus", "audio/aac", ".mp3", ".opus", ".aac"}
        if file_type in no_compress:
            return False
        
        # Compress large WAV files
        if file_size > 50 * 1024 * 1024 and file_type in {"audio/wav", ".wav"}:
            return True
        
        return False
    
    @staticmethod
    def suggest_compression_format(file_type: str) -> str:
        """Suggest best compression format.
        
        Args:
            file_type: Original file type
            
        Returns:
            Recommended format
        """
        # WAV -> OPUS (best compression)
        if file_type in {"audio/wav", ".wav"}:
            return "opus"
        
        return "mp3"
