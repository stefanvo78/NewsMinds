"""
Security utilities for password hashing and JWT tokens.

Uses:
- passlib with bcrypt for password hashing
- python-jose for JWT encoding/decoding
"""

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from jose import jwt, JWTError
from passlib.context import CryptContext

from src.api.core.config import settings


# --- Password Hashing ---

# CryptContext handles hashing algorithm selection and verification
# bcrypt is the recommended algorithm for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password.
    
    Args:
        password: Plain text password from user input
        
    Returns:
        Hashed password string (includes salt, algorithm info)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Password from login attempt
        hashed_password: Stored hash from database
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# --- JWT Tokens ---

ALGORITHM = "HS256"  # HMAC with SHA-256


def create_access_token(subject: uuid.UUID, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The user ID to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode: dict[str, Any] = {
        "sub": str(subject),  # Subject (user ID as string)
        "exp": expire,        # Expiration time
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: The JWT string to decode
        
    Returns:
        Decoded payload dict if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
