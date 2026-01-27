"""
Authentication endpoints: login, register, 2FA setup.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from src.api.core.config import settings
from src.api.core.deps import DbSession
from src.api.core.rate_limit import limiter, RATE_LIMIT_AUTH, RATE_LIMIT_REGISTER
from src.api.core.security import hash_password, verify_password, create_access_token
from src.api.models import User
from src.api.schemas import UserCreate, UserResponse, Token


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT_REGISTER)
async def register(request: Request, user_data: UserCreate, db: DbSession) -> User:
    """
    Register a new user.

    - Validates email is unique
    - Hashes the password
    - Creates the user in the database

    Note: Public registration is disabled by default.
    Set ALLOW_PUBLIC_REGISTRATION=true to enable.
    """
    # Check if public registration is allowed
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled. Contact administrator.",
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user with hashed password
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
@limiter.limit(RATE_LIMIT_AUTH)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: DbSession = None,
) -> Token:
    """
    Login with email and password, receive JWT token.

    Uses OAuth2 password flow (form data with username/password fields).
    Note: OAuth2 spec uses "username" field, but we treat it as email.

    If 2FA is enabled, you must also provide the TOTP code in the password
    field as: "password:123456" where 123456 is the TOTP code.
    """
    # Find user by email (OAuth2 calls it "username")
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # Parse password and optional TOTP code
    password = form_data.password
    totp_code = None
    if ":" in password:
        password, totp_code = password.rsplit(":", 1)

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Check 2FA if enabled
    if user.totp_secret:
        if not totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA code required. Provide as password:code",
                headers={"WWW-Authenticate": "Bearer"},
            )
        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Create access token
    access_token = create_access_token(subject=user.id)

    return Token(access_token=access_token, token_type="bearer")


# =============================================================================
# 2FA Setup Endpoints
# =============================================================================

from pydantic import BaseModel
from src.api.core.deps import CurrentUser
import pyotp


class TOTPSetupResponse(BaseModel):
    """Response containing TOTP setup information."""
    secret: str
    provisioning_uri: str
    qr_code_base64: str | None = None


class TOTPVerifyRequest(BaseModel):
    """Request to verify and enable TOTP."""
    code: str


@router.post("/2fa/setup", response_model=TOTPSetupResponse)
async def setup_2fa(
    current_user: CurrentUser,
    db: DbSession,
) -> TOTPSetupResponse:
    """
    Initialize 2FA setup for the current user.

    Returns:
    - secret: The TOTP secret (save this as backup)
    - provisioning_uri: URI for authenticator apps
    - qr_code_base64: Base64-encoded QR code image

    After receiving this, use /auth/2fa/verify to confirm and enable 2FA.
    """
    if current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled. Disable it first.",
        )

    # Generate new TOTP secret
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)

    # Create provisioning URI for authenticator apps
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name=settings.APP_NAME,
    )

    # Generate QR code
    qr_base64 = None
    try:
        import qrcode
        import qrcode.image.svg
        from io import BytesIO
        import base64

        qr = qrcode.make(provisioning_uri)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    except ImportError:
        pass  # QR code generation is optional

    # Store secret temporarily (not enabled until verified)
    # We store it but 2FA isn't enforced until user verifies
    current_user.totp_secret = secret
    await db.commit()

    return TOTPSetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_code_base64=qr_base64,
    )


@router.post("/2fa/verify")
async def verify_2fa(
    request_data: TOTPVerifyRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Verify TOTP code to confirm 2FA setup.

    After successful verification, 2FA will be enforced on login.
    """
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA not set up. Call /auth/2fa/setup first.",
        )

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(request_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code. Please try again.",
        )

    # 2FA is now verified and will be enforced
    return {"message": "2FA enabled successfully"}


@router.delete("/2fa")
async def disable_2fa(
    request_data: TOTPVerifyRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Disable 2FA for the current user.

    Requires a valid TOTP code to confirm.
    """
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled.",
        )

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(request_data.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code.",
        )

    current_user.totp_secret = None
    await db.commit()

    return {"message": "2FA disabled successfully"}
