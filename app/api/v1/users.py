"""User profile endpoint.

Exposes GET /users/me so the frontend can fetch studio_id, user_id,
and other profile data after login.
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.logging import logger
from app.models.database import get_db
from app.models.user import User
from app.services.studio_service import studio_service

router = APIRouter(prefix="/users", tags=["users"])


class UserProfileResponse(BaseModel):
    """Public user profile returned by GET /users/me."""

    id: int
    email: str
    name: str | None = None
    avatar_url: str | None = None
    provider: str = "email"
    role: str = "regular_user"
    studio_id: str | None = None
    billing_plan_slug: str = "base"


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Return the authenticated user's profile.

    Requires a valid Bearer token (access token or session token).
    Auto-provisions a Studio if the user doesn't have one yet.
    """
    if user.studio_id is None:
        user = await _auto_provision_studio(user, db)

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        provider=user.provider,
        role=user.role,
        studio_id=user.studio_id,
        billing_plan_slug=user.billing_plan_slug,
    )


async def _auto_provision_studio(user: User, db: AsyncSession) -> User:
    """Create a Studio for a user who doesn't have one yet."""
    email_prefix = user.email.split("@")[0]
    short_id = uuid.uuid4().hex[:8]
    slug = f"{email_prefix}-{short_id}"

    studio = await studio_service.create(
        db,
        name=f"Studio di {email_prefix}",
        slug=slug,
    )
    user.studio_id = str(studio.id)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        "auto_provisioned_studio",
        user_id=user.id,
        studio_id=str(studio.id),
        slug=slug,
    )
    return user
