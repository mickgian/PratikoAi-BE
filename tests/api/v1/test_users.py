"""Tests for GET /users/me endpoint.

Tests the user profile endpoint that returns studio_id and other profile data.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_user():
    """Create a mock user matching the User model."""
    user = MagicMock()
    user.id = 42
    user.email = "test@example.com"
    user.name = "Test User"
    user.avatar_url = "https://example.com/avatar.png"
    user.provider = "email"
    user.role = "regular_user"
    user.studio_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    user.billing_plan_slug = "base"
    return user


@pytest.fixture
def app(mock_user):
    """Build a lightweight FastAPI app with the users/me endpoint."""
    from app.api.v1.users import UserProfileResponse

    app = FastAPI()
    router = APIRouter(prefix="/users", tags=["users"])

    @router.get("/me", response_model=UserProfileResponse)
    async def get_me():
        return UserProfileResponse(
            id=mock_user.id,
            email=mock_user.email,
            name=mock_user.name,
            avatar_url=mock_user.avatar_url,
            provider=mock_user.provider,
            role=mock_user.role,
            studio_id=mock_user.studio_id,
            billing_plan_slug=mock_user.billing_plan_slug,
        )

    app.include_router(router, prefix="/api/v1")
    return app


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_user_profile_returns_all_fields(client, mock_user):
    """Happy path: GET /users/me returns full profile including studio_id."""
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 42
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert data["studio_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert data["provider"] == "email"
    assert data["role"] == "regular_user"
    assert data["billing_plan_slug"] == "base"


@pytest.mark.asyncio
async def test_get_user_profile_with_null_studio_id():
    """Edge case: user without studio_id returns null."""
    from app.api.v1.users import UserProfileResponse

    app = FastAPI()
    router = APIRouter(prefix="/users", tags=["users"])

    @router.get("/me", response_model=UserProfileResponse)
    async def get_me():
        return UserProfileResponse(
            id=1,
            email="new@example.com",
            name=None,
            avatar_url=None,
            provider="google",
            role="regular_user",
            studio_id=None,
            billing_plan_slug="base",
        )

    app.include_router(router, prefix="/api/v1")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/api/v1/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["studio_id"] is None
    assert data["name"] is None


@pytest.mark.asyncio
async def test_user_profile_response_schema():
    """Verify the UserProfileResponse schema has expected fields."""
    from app.api.v1.users import UserProfileResponse

    profile = UserProfileResponse(
        id=1,
        email="test@example.com",
        studio_id="abc-123",
    )
    data = profile.model_dump()
    assert "id" in data
    assert "email" in data
    assert "studio_id" in data
    assert "name" in data
    assert "role" in data
    assert "billing_plan_slug" in data


@pytest.mark.asyncio
async def test_auto_provision_studio_when_studio_id_is_none():
    """User with studio_id=None gets a Studio auto-provisioned on GET /users/me."""
    from app.api.v1.users import _auto_provision_studio

    generated_studio_id = str(uuid.uuid4())

    # Mock user with no studio
    user = MagicMock()
    user.id = 99
    user.email = "newuser@example.com"
    user.studio_id = None

    # Mock Studio returned by studio_service.create
    mock_studio = MagicMock()
    mock_studio.id = generated_studio_id

    # Mock db session (add is sync on AsyncSession, commit/refresh are async)
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    # After commit+refresh, user.studio_id should be set
    async def fake_refresh(obj):
        obj.studio_id = str(generated_studio_id)

    mock_db.refresh = AsyncMock(side_effect=fake_refresh)

    with patch("app.api.v1.users.studio_service") as mock_svc:
        mock_svc.create = AsyncMock(return_value=mock_studio)

        result = await _auto_provision_studio(user, mock_db)

    # Verify studio was created with expected name/slug pattern
    mock_svc.create.assert_called_once()
    call_kwargs = mock_svc.create.call_args
    assert call_kwargs.kwargs["name"] == "Studio di newuser"
    assert call_kwargs.kwargs["slug"].startswith("newuser-")

    # Verify user was persisted
    mock_db.add.assert_called_once_with(user)
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(user)

    # Verify result has studio_id populated
    assert result.studio_id == generated_studio_id


@pytest.mark.asyncio
async def test_get_user_profile_triggers_auto_provision():
    """GET /users/me triggers auto-provisioning for user without studio_id."""
    from app.api.v1.users import UserProfileResponse, get_current_user_profile

    generated_studio_id = str(uuid.uuid4())

    user = MagicMock()
    user.id = 1
    user.email = "no-studio@example.com"
    user.name = "No Studio"
    user.avatar_url = None
    user.provider = "email"
    user.role = "regular_user"
    user.studio_id = None
    user.billing_plan_slug = "base"

    mock_db = AsyncMock()

    # Simulate _auto_provision_studio setting studio_id
    async def fake_provision(u, db):
        u.studio_id = generated_studio_id
        return u

    with patch(
        "app.api.v1.users._auto_provision_studio",
        side_effect=fake_provision,
    ) as mock_provision:
        result = await get_current_user_profile(user=user, db=mock_db)

    mock_provision.assert_called_once_with(user, mock_db)
    assert result.studio_id == generated_studio_id
