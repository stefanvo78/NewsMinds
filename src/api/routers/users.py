"""
User profile endpoints.
"""

from fastapi import APIRouter

from src.api.core.deps import CurrentUser
from src.api.schemas import UserResponse


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: CurrentUser) -> CurrentUser:
    """
    Get the current authenticated user's profile.

    Requires a valid JWT token in the Authorization header.
    """
    return current_user
