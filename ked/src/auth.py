"""JWT authentication and authorization utilities."""

import logging
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

from .config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()


class JWTConfig:
    """JWT configuration."""
    algorithm = "HS256"
    
    @classmethod
    def get_secret_key(cls) -> str:
        """Get JWT secret key from settings."""
        if not settings.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY not configured in environment")
        return settings.jwt_secret_key


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.
    
    Args:
        user_id: User ID to encode in token
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=settings.jwt_expiration_hours)
    
    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    token = jwt.encode(
        payload,
        JWTConfig.get_secret_key(),
        algorithm=JWTConfig.algorithm,
    )
    return token


def verify_token(token: str) -> int:
    """Verify JWT token and return user_id.
    
    Args:
        token: JWT token string
        
    Returns:
        user_id from token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            JWTConfig.get_secret_key(),
            algorithms=[JWTConfig.algorithm],
        )
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: user_id not found",
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)) -> int:
    """Dependency to extract and verify user_id from JWT token.
    
    Args:
        credentials: Bearer token from request header
        
    Returns:
        user_id
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    return verify_token(token)
