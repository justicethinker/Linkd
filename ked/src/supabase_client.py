"""Supabase client initialization and helper functions.

Provides:
1. Supabase client instance
2. Authentication helpers
3. Storage operations
4. Database operations
"""

import logging
from typing import Optional
from supabase import create_client, Client
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

from .config import settings
from .exceptions import UnauthorizedError

logger = logging.getLogger(__name__)
security = HTTPBearer()


class SupabaseManager:
    """Manages Supabase client and operations."""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client.
        
        Returns:
            Supabase client instance
            
        Raises:
            ValueError: If Supabase configuration is missing
        """
        if cls._instance is not None:
            return cls._instance
        
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise ValueError(
                "Supabase URL and anon key must be configured in environment variables"
            )
        
        cls._instance = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_anon_key,
        )
        
        logger.info(f"✓ Supabase client initialized: {settings.supabase_url}")
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset client instance (for testing)."""
        cls._instance = None


def get_supabase_client() -> Client:
    """FastAPI dependency to get Supabase client.
    
    Returns:
        Supabase client instance
    """
    return SupabaseManager.get_client()


async def verify_supabase_token(credentials: HTTPAuthCredentials = Depends(security)) -> dict:
    """Verify Supabase JWT token from Authorization header.
    
    This dependency validates that the request contains a valid Supabase
    JWT token (either user token or service role key).
    
    Args:
        credentials: HTTP Bearer credentials from Authorization header
        
    Returns:
        Decoded token payload with user_id and session info
        
    Raises:
        HTTPException: If token is invalid or verification fails
    """
    token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        client = SupabaseManager.get_client()
        
        # Verify token with Supabase auth
        response = client.auth.get_user(token)
        
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(f"✓ Token verified for user: {response.user.id}")
        
        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "token": token,
            "user": response.user,
        }
    
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(auth_data: dict = Depends(verify_supabase_token)) -> str:
    """FastAPI dependency to get current authenticated user ID.
    
    Args:
        auth_data: Verified token data from verify_supabase_token
        
    Returns:
        User ID (UUID string from Supabase)
    """
    return auth_data["user_id"]


def get_current_user_data(auth_data: dict = Depends(verify_supabase_token)) -> dict:
    """FastAPI dependency to get current authenticated user full data.
    
    Args:
        auth_data: Verified token data from verify_supabase_token
        
    Returns:
        Complete user data including id, email, user object
    """
    return auth_data


class SupabaseStorage:
    """Helper class for Supabase storage operations."""
    
    def __init__(self, client: Client = None):
        """Initialize storage helper.
        
        Args:
            client: Supabase client instance (defaults to shared instance)
        """
        self.client = client or SupabaseManager.get_client()
    
    async def upload_file(
        self,
        bucket: str,
        path: str,
        file_data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to Supabase storage.
        
        Args:
            bucket: Storage bucket name
            path: File path in bucket (e.g., "user_123/audio_456.wav")
            file_data: Binary file data
            content_type: MIME type of file
            
        Returns:
            Public URL of uploaded file
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Upload to Supabase storage
            response = self.client.storage.from_(bucket).upload(
                path=path,
                file=file_data,
                file_options={"content-type": content_type},
            )
            
            logger.info(f"✓ Uploaded file to {bucket}/{path}")
            
            # Get public URL
            url = self.client.storage.from_(bucket).get_public_url(path)
            return url
        
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    async def delete_file(self, bucket: str, path: str) -> bool:
        """Delete file from Supabase storage.
        
        Args:
            bucket: Storage bucket name
            path: File path in bucket
            
        Returns:
            True if deletion successful
            
        Raises:
            Exception: If deletion fails
        """
        try:
            self.client.storage.from_(bucket).remove([path])
            logger.info(f"✓ Deleted file from {bucket}/{path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            raise
    
    async def get_file(self, bucket: str, path: str) -> bytes:
        """Download file from Supabase storage.
        
        Args:
            bucket: Storage bucket name
            path: File path in bucket
            
        Returns:
            Binary file data
            
        Raises:
            Exception: If download fails
        """
        try:
            response = self.client.storage.from_(bucket).download(path)
            logger.info(f"✓ Downloaded file from {bucket}/{path}")
            return response
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise
    
    def get_public_url(self, bucket: str, path: str) -> str:
        """Get public URL for a file in storage.
        
        Args:
            bucket: Storage bucket name
            path: File path in bucket
            
        Returns:
            Public URL of the file
        """
        return self.client.storage.from_(bucket).get_public_url(path)


class SupabaseDatabase:
    """Helper class for Supabase database operations."""
    
    def __init__(self, client: Client = None):
        """Initialize database helper.
        
        Args:
            client: Supabase client instance (defaults to shared instance)
        """
        self.client = client or SupabaseManager.get_client()
    
    async def get_user_profile(self, user_id: str) -> dict:
        """Get user profile from database.
        
        Args:
            user_id: User UUID from Supabase auth
            
        Returns:
            User profile data
            
        Raises:
            Exception: If query fails
        """
        try:
            response = self.client.table("user_profiles").select("*").eq(
                "user_id", user_id
            ).single().execute()
            
            logger.debug(f"✓ Retrieved profile for user: {user_id}")
            return response.data
        
        except Exception as e:
            logger.warning(f"Failed to get user profile: {e}")
            return None
    
    async def create_user_profile(self, user_id: str, data: dict) -> dict:
        """Create user profile in database.
        
        Args:
            user_id: User UUID from Supabase auth
            data: Profile data to store
            
        Returns:
            Created profile data
            
        Raises:
            Exception: If insert fails
        """
        try:
            profile_data = {"user_id": user_id, **data}
            response = self.client.table("user_profiles").insert(profile_data).execute()
            
            logger.info(f"✓ Created profile for user: {user_id}")
            return response.data[0]
        
        except Exception as e:
            logger.error(f"Failed to create user profile: {e}")
            raise
    
    async def update_user_profile(self, user_id: str, data: dict) -> dict:
        """Update user profile in database.
        
        Args:
            user_id: User UUID from Supabase auth
            data: Profile data to update
            
        Returns:
            Updated profile data
            
        Raises:
            Exception: If update fails
        """
        try:
            response = self.client.table("user_profiles").update(data).eq(
                "user_id", user_id
            ).execute()
            
            logger.info(f"✓ Updated profile for user: {user_id}")
            return response.data[0] if response.data else None
        
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            raise
    
    async def insert(self, table: str, data: dict) -> dict:
        """Generic insert operation.
        
        Args:
            table: Table name
            data: Data to insert
            
        Returns:
            Inserted data
            
        Raises:
            Exception: If insert fails
        """
        try:
            response = self.client.table(table).insert(data).execute()
            logger.debug(f"✓ Inserted record in {table}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to insert in {table}: {e}")
            raise
    
    async def query(self, table: str, **filters) -> list:
        """Generic query operation.
        
        Args:
            table: Table name
            **filters: Column=value filters
            
        Returns:
            List of matching records
            
        Raises:
            Exception: If query fails
        """
        try:
            query = self.client.table(table).select("*")
            
            for col, val in filters.items():
                query = query.eq(col, val)
            
            response = query.execute()
            logger.debug(f"✓ Queried {table} with filters: {filters}")
            return response.data
        
        except Exception as e:
            logger.error(f"Failed to query {table}: {e}")
            raise


def get_supabase_storage(client: Client = Depends(get_supabase_client)) -> SupabaseStorage:
    """FastAPI dependency to get Supabase storage helper.
    
    Args:
        client: Supabase client from dependency injection
        
    Returns:
        SupabaseStorage instance
    """
    return SupabaseStorage(client)


def get_supabase_database(client: Client = Depends(get_supabase_client)) -> SupabaseDatabase:
    """FastAPI dependency to get Supabase database helper.
    
    Args:
        client: Supabase client from dependency injection
        
    Returns:
        SupabaseDatabase instance
    """
    return SupabaseDatabase(client)
