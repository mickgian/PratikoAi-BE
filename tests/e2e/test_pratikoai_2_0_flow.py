"""DEV-371: Full User Journey E2E Test — PratikoAI 2.0 Validation.

Comprehensive E2E test covering the entire PratikoAI 2.0 user journey:
1. Register → 2. Create Studio → 3. Import Clients → 4. Chat →
5. View Matches → 6. Create Communication → 7. Approve → 8. Send →
9. View Dashboard

Coverage: ≥70% new code.  Tests run against real FastAPI app with database.

NOTE: Skipped in CI — requires real PostgreSQL database connection.
"""

from __future__ import annotations

import os

import pytest  # isort: skip

# Skip at module level when no database is available (CI environment).
_pg_url = os.environ.get("POSTGRES_URL", "")
if not _pg_url or "localhost" in _pg_url:
    try:
        import psycopg2

        conn = psycopg2.connect(_pg_url or "postgresql://test:test@localhost:5432/pratikoai_test", connect_timeout=2)
        conn.close()
    except Exception:
        pytest.skip(
            "E2E full journey tests require real PostgreSQL database — skipped in CI",
            allow_module_level=True,
        )

from uuid import uuid4  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.main import app  # noqa: E402
from app.models.database import get_db  # noqa: E402

# ============================================================================
# Helpers
# ============================================================================


def _unique_email() -> str:
    """Generate a unique email for each test run."""
    return f"e2e_journey_{uuid4().hex[:8]}@test.pratikoai.com"


def _unique_slug() -> str:
    """Generate a unique slug for each test run."""
    return f"studio-e2e-{uuid4().hex[:8]}"


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession):
    """Create an async HTTP client with DB override."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_email() -> str:
    return _unique_email()


@pytest.fixture
def test_slug() -> str:
    return _unique_slug()


@pytest.fixture
def test_password() -> str:
    return "TestPass1!"


# ============================================================================
# Step 1: Registration
# ============================================================================


class TestStep1Registration:
    """Step 1: User registration."""

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        async_client: AsyncClient,
        test_email: str,
        test_password: str,
    ):
        """Happy path: register a new user and receive tokens."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": test_email, "password": test_password},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_email
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["id"] > 0

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        async_client: AsyncClient,
        test_password: str,
    ):
        """Error case: registering with an already-used email returns 400."""
        email = _unique_email()
        # First registration
        resp1 = await async_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": test_password},
        )
        assert resp1.status_code == 200

        # Duplicate
        resp2 = await async_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": test_password},
        )
        assert resp2.status_code == 400
        assert "already registered" in resp2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client: AsyncClient):
        """Edge case: weak password is rejected (422)."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": _unique_email(), "password": "weak"},
        )
        assert response.status_code == 422


# ============================================================================
# Step 2: Create Studio
# ============================================================================


class TestStep2CreateStudio:
    """Step 2: Studio creation."""

    @pytest.mark.asyncio
    async def test_create_studio_success(
        self,
        async_client: AsyncClient,
        test_slug: str,
    ):
        """Happy path: create a studio and verify response."""
        response = await async_client.post(
            "/api/v1/studios",
            json={
                "name": "Studio E2E Test",
                "slug": test_slug,
                "max_clients": 50,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Studio E2E Test"
        assert data["slug"] == test_slug
        assert data["max_clients"] == 50
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_studio_duplicate_slug(
        self,
        async_client: AsyncClient,
    ):
        """Error case: duplicate slug returns 400."""
        slug = _unique_slug()
        resp1 = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio 1", "slug": slug},
        )
        assert resp1.status_code == 201

        resp2 = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio 2", "slug": slug},
        )
        assert resp2.status_code == 400

    @pytest.mark.asyncio
    async def test_get_studio_by_id(
        self,
        async_client: AsyncClient,
    ):
        """Verify studio retrieval by ID."""
        slug = _unique_slug()
        create_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Lookup", "slug": slug},
        )
        studio_id = create_resp.json()["id"]

        get_resp = await async_client.get(f"/api/v1/studios/{studio_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["slug"] == slug


# ============================================================================
# Step 3: Import Clients
# ============================================================================


class TestStep3ImportClients:
    """Step 3: Client creation/import."""

    @pytest_asyncio.fixture
    async def studio_id(self, async_client: AsyncClient) -> str:
        """Create a studio and return its ID."""
        resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Clienti", "slug": _unique_slug()},
        )
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_create_single_client(
        self,
        async_client: AsyncClient,
        studio_id: str,
    ):
        """Happy path: create a single client."""
        response = await async_client.post(
            "/api/v1/clients",
            params={"studio_id": studio_id},
            json={
                "codice_fiscale": "RSSMRA80A01H501Z",
                "nome": "Mario Rossi",
                "tipo_cliente": "persona_fisica",
                "comune": "Roma",
                "provincia": "RM",
                "email": "mario.rossi@example.com",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Mario Rossi"
        assert data["studio_id"] == studio_id
        assert data["stato_cliente"] == "attivo"

    @pytest.mark.asyncio
    async def test_create_multiple_clients(
        self,
        async_client: AsyncClient,
        studio_id: str,
    ):
        """Create multiple clients and verify listing."""
        clients_data = [
            {
                "codice_fiscale": "BNCGVN75D15F205X",
                "nome": "Giovanni Bianchi",
                "tipo_cliente": "persona_fisica",
                "comune": "Milano",
                "provincia": "MI",
            },
            {
                "codice_fiscale": "VRDLRA85M01L219P",
                "nome": "Laura Verdi SRL",
                "tipo_cliente": "societa",
                "comune": "Torino",
                "provincia": "TO",
                "partita_iva": "12345678901",
            },
        ]

        for client_data in clients_data:
            resp = await async_client.post(
                "/api/v1/clients",
                params={"studio_id": studio_id},
                json=client_data,
            )
            assert resp.status_code == 201

        # Verify listing
        list_resp = await async_client.get(
            "/api/v1/clients",
            params={"studio_id": studio_id},
        )
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_client_not_found_wrong_studio(
        self,
        async_client: AsyncClient,
        studio_id: str,
    ):
        """Tenant isolation: client from another studio returns 404."""
        # Create a client in studio_id
        resp = await async_client.post(
            "/api/v1/clients",
            params={"studio_id": studio_id},
            json={
                "codice_fiscale": "TSTCLN90A01H501Z",
                "nome": "Test Isolation",
                "tipo_cliente": "persona_fisica",
                "comune": "Roma",
                "provincia": "RM",
            },
        )
        client_id = resp.json()["id"]

        # Try to access with a different studio
        other_studio_id = str(uuid4())
        get_resp = await async_client.get(
            f"/api/v1/clients/{client_id}",
            params={"studio_id": other_studio_id},
        )
        assert get_resp.status_code == 404


# ============================================================================
# Step 4: Chat (mocked LLM)
# ============================================================================


class TestStep4Chat:
    """Step 4: Chat interaction (LLM mocked to avoid real API calls)."""

    @pytest.mark.asyncio
    async def test_chat_requires_session_auth(self, async_client: AsyncClient):
        """Error case: chat without auth returns 403."""
        response = await async_client.post(
            "/api/v1/chatbot/chat",
            json={
                "messages": [{"role": "user", "content": "Ciao, come funziona?"}],
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_chat_empty_messages_rejected(self, async_client: AsyncClient):
        """Edge case: empty messages list returns 422."""
        response = await async_client.post(
            "/api/v1/chatbot/chat",
            json={"messages": []},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code == 422


# ============================================================================
# Step 5: View Matches
# ============================================================================


class TestStep5ViewMatches:
    """Step 5: View matching suggestions."""

    @pytest_asyncio.fixture
    async def studio_with_suggestion(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> str:
        """Create a studio and seed a proactive suggestion."""
        from app.models.proactive_suggestion import ProactiveSuggestion

        # Create studio
        resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Match", "slug": _unique_slug()},
        )
        studio_id = resp.json()["id"]

        # Create a knowledge_items row for FK
        from sqlalchemy import text

        await db_session.execute(
            text(
                "INSERT INTO knowledge_items (id, source, title, content, content_type) "
                "VALUES (99990, 'e2e_test', 'Test KB', 'Test content', 'normativa') "
                "ON CONFLICT (id) DO NOTHING"
            )
        )

        # Seed a suggestion
        suggestion = ProactiveSuggestion(
            studio_id=studio_id,
            knowledge_item_id=99990,
            matched_client_ids=[1, 2],
            match_score=0.85,
            suggestion_text="Nuova normativa fiscale rilevante per 2 clienti",
        )
        db_session.add(suggestion)
        await db_session.flush()

        return studio_id

    @pytest.mark.asyncio
    async def test_list_suggestions_success(
        self,
        async_client: AsyncClient,
        studio_with_suggestion: str,
    ):
        """Happy path: list matching suggestions for a studio."""
        response = await async_client.get(
            "/api/v1/matching/suggestions",
            headers={"x-studio-id": studio_with_suggestion},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        suggestion = data[0]
        assert suggestion["match_score"] == 0.85
        assert suggestion["is_read"] is False

    @pytest.mark.asyncio
    async def test_list_suggestions_empty_studio(
        self,
        async_client: AsyncClient,
    ):
        """Edge case: empty studio returns empty list."""
        resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Vuoto", "slug": _unique_slug()},
        )
        studio_id = resp.json()["id"]
        response = await async_client.get(
            "/api/v1/matching/suggestions",
            headers={"x-studio-id": studio_id},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_trigger_matching_accepted(
        self,
        async_client: AsyncClient,
    ):
        """Happy path: trigger matching job returns 202 accepted."""
        resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Trigger", "slug": _unique_slug()},
        )
        studio_id = resp.json()["id"]

        response = await async_client.post(
            "/api/v1/matching/trigger",
            headers={"x-studio-id": studio_id},
            json={"trigger": "manual"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["studio_id"] == studio_id


# ============================================================================
# Step 6: Create Communication
# ============================================================================


class TestStep6CreateCommunication:
    """Step 6: Create a communication draft."""

    @pytest_asyncio.fixture
    async def studio_and_client(self, async_client: AsyncClient) -> tuple[str, int]:
        """Create a studio with a client, return (studio_id, client_id)."""
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Comm", "slug": _unique_slug()},
        )
        studio_id = studio_resp.json()["id"]

        client_resp = await async_client.post(
            "/api/v1/clients",
            params={"studio_id": studio_id},
            json={
                "codice_fiscale": "CMMNTN80A01H501Z",
                "nome": "Antonio Comunicazione",
                "tipo_cliente": "persona_fisica",
                "comune": "Napoli",
                "provincia": "NA",
                "email": "antonio@example.com",
            },
        )
        client_id = client_resp.json()["id"]
        return studio_id, client_id

    @pytest.mark.asyncio
    async def test_create_draft_communication(
        self,
        async_client: AsyncClient,
        studio_and_client: tuple[str, int],
    ):
        """Happy path: create a communication draft."""
        studio_id, client_id = studio_and_client
        response = await async_client.post(
            "/api/v1/communications",
            params={"studio_id": studio_id, "created_by": 1},
            json={
                "subject": "Aggiornamento Normativa IVA",
                "content": "Gentile cliente, la informiamo che...",
                "channel": "email",
                "client_id": client_id,
                "normativa_riferimento": "DL 73/2025",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"
        assert data["subject"] == "Aggiornamento Normativa IVA"
        assert data["client_id"] == client_id
        assert data["studio_id"] == studio_id

    @pytest.mark.asyncio
    async def test_create_communication_without_client(
        self,
        async_client: AsyncClient,
        studio_and_client: tuple[str, int],
    ):
        """Edge case: communication without client (broadcast)."""
        studio_id, _ = studio_and_client
        response = await async_client.post(
            "/api/v1/communications",
            params={"studio_id": studio_id, "created_by": 1},
            json={
                "subject": "Avviso Generale",
                "content": "Comunicazione a tutti i clienti.",
                "channel": "email",
            },
        )
        assert response.status_code == 201
        assert response.json()["client_id"] is None


# ============================================================================
# Step 7: Approve Communication
# ============================================================================


class TestStep7ApproveCommunication:
    """Step 7: Communication approval workflow."""

    @pytest_asyncio.fixture
    async def draft_communication(self, async_client: AsyncClient) -> tuple[str, str]:
        """Create studio and a draft communication.

        Returns (studio_id, communication_id).
        """
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Approvazione", "slug": _unique_slug()},
        )
        studio_id = studio_resp.json()["id"]

        comm_resp = await async_client.post(
            "/api/v1/communications",
            params={"studio_id": studio_id, "created_by": 1},
            json={
                "subject": "Comunicazione da Approvare",
                "content": "Contenuto della comunicazione.",
                "channel": "email",
            },
        )
        comm_id = comm_resp.json()["id"]
        return studio_id, comm_id

    @pytest.mark.asyncio
    async def test_approve_workflow(
        self,
        async_client: AsyncClient,
        draft_communication: tuple[str, str],
    ):
        """Happy path: DRAFT → PENDING_REVIEW → APPROVED."""
        studio_id, comm_id = draft_communication

        # Submit for review
        submit_resp = await async_client.post(
            f"/api/v1/communications/{comm_id}/submit",
            params={"studio_id": studio_id},
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "pending_review"

        # Approve
        approve_resp = await async_client.post(
            f"/api/v1/communications/{comm_id}/approve",
            params={"studio_id": studio_id, "approved_by": 2},
        )
        assert approve_resp.status_code == 200
        data = approve_resp.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == 2
        assert data["approved_at"] is not None

    @pytest.mark.asyncio
    async def test_reject_workflow(
        self,
        async_client: AsyncClient,
        draft_communication: tuple[str, str],
    ):
        """Alternative path: DRAFT → PENDING_REVIEW → REJECTED."""
        studio_id, comm_id = draft_communication

        await async_client.post(
            f"/api/v1/communications/{comm_id}/submit",
            params={"studio_id": studio_id},
        )

        reject_resp = await async_client.post(
            f"/api/v1/communications/{comm_id}/reject",
            params={"studio_id": studio_id},
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_approve_without_submit_fails(
        self,
        async_client: AsyncClient,
        draft_communication: tuple[str, str],
    ):
        """Error case: cannot approve a DRAFT directly (must submit first)."""
        studio_id, comm_id = draft_communication

        approve_resp = await async_client.post(
            f"/api/v1/communications/{comm_id}/approve",
            params={"studio_id": studio_id, "approved_by": 2},
        )
        assert approve_resp.status_code == 400


# ============================================================================
# Step 8: Send Communication
# ============================================================================


class TestStep8SendCommunication:
    """Step 8: Mark communication as sent."""

    @pytest_asyncio.fixture
    async def approved_communication(self, async_client: AsyncClient) -> tuple[str, str]:
        """Create, submit, and approve a communication.

        Returns (studio_id, communication_id).
        """
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Invio", "slug": _unique_slug()},
        )
        studio_id = studio_resp.json()["id"]

        comm_resp = await async_client.post(
            "/api/v1/communications",
            params={"studio_id": studio_id, "created_by": 1},
            json={
                "subject": "Comunicazione da Inviare",
                "content": "Contenuto pronto per invio.",
                "channel": "email",
            },
        )
        comm_id = comm_resp.json()["id"]

        # Submit for review
        await async_client.post(
            f"/api/v1/communications/{comm_id}/submit",
            params={"studio_id": studio_id},
        )

        # Approve
        await async_client.post(
            f"/api/v1/communications/{comm_id}/approve",
            params={"studio_id": studio_id, "approved_by": 2},
        )

        return studio_id, comm_id

    @pytest.mark.asyncio
    async def test_send_approved_communication(
        self,
        async_client: AsyncClient,
        approved_communication: tuple[str, str],
    ):
        """Happy path: APPROVED → SENT with timestamp."""
        studio_id, comm_id = approved_communication

        send_resp = await async_client.post(
            f"/api/v1/communications/{comm_id}/send",
            params={"studio_id": studio_id},
        )
        assert send_resp.status_code == 200
        data = send_resp.json()
        assert data["status"] == "sent"
        assert data["sent_at"] is not None

    @pytest.mark.asyncio
    async def test_send_draft_fails(
        self,
        async_client: AsyncClient,
    ):
        """Error case: cannot send a DRAFT directly."""
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Send Fail", "slug": _unique_slug()},
        )
        studio_id = studio_resp.json()["id"]

        comm_resp = await async_client.post(
            "/api/v1/communications",
            params={"studio_id": studio_id, "created_by": 1},
            json={
                "subject": "Non Inviabile",
                "content": "Questa è ancora una bozza.",
                "channel": "email",
            },
        )
        comm_id = comm_resp.json()["id"]

        send_resp = await async_client.post(
            f"/api/v1/communications/{comm_id}/send",
            params={"studio_id": studio_id},
        )
        assert send_resp.status_code == 400

    @pytest.mark.asyncio
    async def test_communication_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Error case: send for nonexistent communication returns 404."""
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio 404", "slug": _unique_slug()},
        )
        studio_id = studio_resp.json()["id"]
        fake_id = str(uuid4())

        send_resp = await async_client.post(
            f"/api/v1/communications/{fake_id}/send",
            params={"studio_id": studio_id},
        )
        assert send_resp.status_code == 404


# ============================================================================
# Step 9: View Dashboard
# ============================================================================


class TestStep9ViewDashboard:
    """Step 9: Dashboard aggregation."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_data(
        self,
        async_client: AsyncClient,
    ):
        """Happy path: dashboard returns aggregated data."""
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Dashboard", "slug": _unique_slug()},
        )
        studio_id = studio_resp.json()["id"]

        response = await async_client.get(
            "/api/v1/dashboard",
            params={"studio_id": studio_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_dashboard_empty_studio(
        self,
        async_client: AsyncClient,
    ):
        """Edge case: dashboard for studio with no data."""
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Vuoto Dash", "slug": _unique_slug()},
        )
        studio_id = studio_resp.json()["id"]

        response = await async_client.get(
            "/api/v1/dashboard",
            params={"studio_id": studio_id},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalidate_dashboard_cache(
        self,
        async_client: AsyncClient,
    ):
        """Verify cache invalidation endpoint works."""
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Cache", "slug": _unique_slug()},
        )
        studio_id = studio_resp.json()["id"]

        response = await async_client.post(
            "/api/v1/dashboard/invalidate-cache",
            params={"studio_id": studio_id},
        )
        assert response.status_code == 204


# ============================================================================
# Full Journey: Integrated end-to-end flow
# ============================================================================


class TestFullJourney:
    """Complete PratikoAI 2.0 user journey in a single sequential test."""

    @pytest.mark.asyncio
    async def test_complete_user_journey(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Full journey: Register → Studio → Clients → Matches → Comm → Approve → Send → Dashboard."""
        # ── Step 1: Register ──
        email = _unique_email()
        reg_resp = await async_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "JourneyTest1!"},
        )
        assert reg_resp.status_code == 200
        user_data = reg_resp.json()
        user_id = user_data["id"]
        assert user_data["access_token"]  # token returned

        # ── Step 2: Create Studio ──
        slug = _unique_slug()
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Percorso Completo", "slug": slug, "max_clients": 200},
        )
        assert studio_resp.status_code == 201
        studio_id = studio_resp.json()["id"]

        # ── Step 3: Import Clients ──
        client1_resp = await async_client.post(
            "/api/v1/clients",
            params={"studio_id": studio_id},
            json={
                "codice_fiscale": "JRNCL180A01H501A",
                "nome": "Cliente Uno",
                "tipo_cliente": "persona_fisica",
                "comune": "Roma",
                "provincia": "RM",
                "email": "cliente1@example.com",
            },
        )
        assert client1_resp.status_code == 201
        client1_id = client1_resp.json()["id"]

        client2_resp = await async_client.post(
            "/api/v1/clients",
            params={"studio_id": studio_id},
            json={
                "codice_fiscale": "JRNCL280B02L219B",
                "nome": "Cliente Due SRL",
                "tipo_cliente": "societa",
                "comune": "Milano",
                "provincia": "MI",
                "partita_iva": "98765432109",
            },
        )
        assert client2_resp.status_code == 201

        # Verify listing
        list_resp = await async_client.get(
            "/api/v1/clients",
            params={"studio_id": studio_id},
        )
        assert list_resp.json()["total"] == 2

        # ── Step 4: Chat (auth required — skip real LLM) ──
        # Verify that chat endpoint exists and requires auth
        chat_resp = await async_client.post(
            "/api/v1/chatbot/chat",
            json={"messages": [{"role": "user", "content": "Quali scadenze ho?"}]},
        )
        assert chat_resp.status_code == 403  # No session token

        # ── Step 5: View Matches ──
        matches_resp = await async_client.get(
            "/api/v1/matching/suggestions",
            headers={"x-studio-id": studio_id},
        )
        assert matches_resp.status_code == 200
        assert isinstance(matches_resp.json(), list)

        # Trigger matching
        trigger_resp = await async_client.post(
            "/api/v1/matching/trigger",
            headers={"x-studio-id": studio_id},
            json={"trigger": "manual"},
        )
        assert trigger_resp.status_code == 202

        # ── Step 6: Create Communication ──
        comm_resp = await async_client.post(
            "/api/v1/communications",
            params={"studio_id": studio_id, "created_by": user_id},
            json={
                "subject": "Aggiornamento IVA Q1 2026",
                "content": (
                    "Gentile Cliente Uno,\n\n"
                    "Le comunichiamo che la normativa IVA è stata aggiornata. "
                    "La preghiamo di contattarci per maggiori informazioni.\n\n"
                    "Cordiali saluti,\nStudio Percorso Completo"
                ),
                "channel": "email",
                "client_id": client1_id,
                "normativa_riferimento": "Art. 10 DPR 633/72",
            },
        )
        assert comm_resp.status_code == 201
        comm_data = comm_resp.json()
        comm_id = comm_data["id"]
        assert comm_data["status"] == "draft"
        assert comm_data["created_by"] == user_id

        # ── Step 7: Submit & Approve ──
        submit_resp = await async_client.post(
            f"/api/v1/communications/{comm_id}/submit",
            params={"studio_id": studio_id},
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "pending_review"

        approve_resp = await async_client.post(
            f"/api/v1/communications/{comm_id}/approve",
            params={"studio_id": studio_id, "approved_by": user_id},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        # ── Step 8: Send ──
        send_resp = await async_client.post(
            f"/api/v1/communications/{comm_id}/send",
            params={"studio_id": studio_id},
        )
        assert send_resp.status_code == 200
        sent_data = send_resp.json()
        assert sent_data["status"] == "sent"
        assert sent_data["sent_at"] is not None

        # Verify final state via GET
        final_comm = await async_client.get(
            f"/api/v1/communications/{comm_id}",
            params={"studio_id": studio_id},
        )
        assert final_comm.status_code == 200
        assert final_comm.json()["status"] == "sent"

        # ── Step 9: View Dashboard ──
        dash_resp = await async_client.get(
            "/api/v1/dashboard",
            params={"studio_id": studio_id},
        )
        assert dash_resp.status_code == 200
        dash_data = dash_resp.json()
        assert isinstance(dash_data, dict)

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation(
        self,
        async_client: AsyncClient,
    ):
        """Verify that data from one studio is not accessible from another."""
        # Create two studios
        studio1_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Alpha", "slug": _unique_slug()},
        )
        studio1_id = studio1_resp.json()["id"]

        studio2_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Beta", "slug": _unique_slug()},
        )
        studio2_id = studio2_resp.json()["id"]

        # Create client in studio 1
        client_resp = await async_client.post(
            "/api/v1/clients",
            params={"studio_id": studio1_id},
            json={
                "codice_fiscale": "TNTISL90A01H501Z",
                "nome": "Isolamento Tenant",
                "tipo_cliente": "persona_fisica",
                "comune": "Firenze",
                "provincia": "FI",
            },
        )
        client_id = client_resp.json()["id"]

        # Studio 2 cannot see studio 1's clients
        list_resp = await async_client.get(
            "/api/v1/clients",
            params={"studio_id": studio2_id},
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 0

        # Direct access also blocked
        get_resp = await async_client.get(
            f"/api/v1/clients/{client_id}",
            params={"studio_id": studio2_id},
        )
        assert get_resp.status_code == 404

        # Communication in studio 1 not visible from studio 2
        comm_resp = await async_client.post(
            "/api/v1/communications",
            params={"studio_id": studio1_id, "created_by": 1},
            json={
                "subject": "Studio 1 Only",
                "content": "Riservato allo studio 1.",
                "channel": "email",
            },
        )
        comm_id = comm_resp.json()["id"]

        get_comm = await async_client.get(
            f"/api/v1/communications/{comm_id}",
            params={"studio_id": studio2_id},
        )
        assert get_comm.status_code == 404

    @pytest.mark.asyncio
    async def test_bulk_communication_workflow(
        self,
        async_client: AsyncClient,
    ):
        """Full workflow with bulk communications to multiple clients."""
        # Setup studio + clients
        studio_resp = await async_client.post(
            "/api/v1/studios",
            json={"name": "Studio Bulk", "slug": _unique_slug()},
        )
        studio_id = studio_resp.json()["id"]

        client_ids = []
        for i in range(3):
            cf = f"BLKCL{i}80A0{i}H501Z"
            resp = await async_client.post(
                "/api/v1/clients",
                params={"studio_id": studio_id},
                json={
                    "codice_fiscale": cf,
                    "nome": f"Cliente Bulk {i}",
                    "tipo_cliente": "persona_fisica",
                    "comune": "Roma",
                    "provincia": "RM",
                },
            )
            assert resp.status_code == 201
            client_ids.append(resp.json()["id"])

        # Create bulk communications
        bulk_resp = await async_client.post(
            "/api/v1/communications/bulk",
            params={"studio_id": studio_id, "created_by": 1},
            json={
                "client_ids": client_ids,
                "subject": "Comunicazione Massiva",
                "content": "Aggiornamento per tutti i clienti.",
                "channel": "email",
            },
        )
        assert bulk_resp.status_code == 201
        comms = bulk_resp.json()
        assert len(comms) == 3

        # All should be drafts
        for comm in comms:
            assert comm["status"] == "draft"
