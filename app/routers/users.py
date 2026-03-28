"""User endpoints: profile, update, change password, admin user list."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User
from app.schemas import ChangePasswordRequest, UpdateProfileRequest, UserResponse
from app.security import hash_password, verify_password

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Update the authenticated user's profile fields."""
    if body.username and body.username != current_user.username:
        taken = await db.execute(select(User).where(User.username == body.username))
        if taken.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken.",
            )
        current_user.username = body.username

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Change the authenticated user's password."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()


# ---------------------------------------------------------------------------
# Admin-only endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[UserResponse],
    dependencies=[Depends(require_role("admin"))],
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 50,
) -> list[User]:
    """[Admin] List all registered users with pagination."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


@router.patch(
    "/{user_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("admin"))],
)
async def deactivate_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """[Admin] Deactivate a user account by ID."""
    from uuid import UUID
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_active = False
    await db.commit()
