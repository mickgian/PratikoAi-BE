"""DEV-335: Tests for CommunicationService.create_bulk_drafts — Bulk communication creation.

TDD RED phase: These tests define the expected behaviour of the bulk draft
creation method on the existing CommunicationService.  The method does not
exist yet; running these tests must produce AttributeError failures until
the GREEN phase implementation is completed.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.communication import CanaleInvio, Communication, StatoComunicazione
from app.services.communication_service import CommunicationService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def comm_service() -> CommunicationService:
    return CommunicationService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def other_studio_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBulkCommunicationService:
    """Test CommunicationService.create_bulk_drafts()."""

    @pytest.mark.asyncio
    async def test_create_bulk_drafts(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Happy path: create drafts for multiple clients at once."""
        client_ids = [1, 2, 3]

        # Mock DB returning all clients as valid for the studio
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[MagicMock(id=cid) for cid in client_ids]))
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await comm_service.create_bulk_drafts(
            db=mock_db,
            studio_id=studio_id,
            client_ids=client_ids,
            subject="Scadenza IVA trimestrale",
            content="Gentile cliente, le ricordiamo la scadenza IVA del 16 marzo.",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )

        assert len(results) == 3
        for comm in results:
            assert comm.status == StatoComunicazione.DRAFT
            assert comm.studio_id == studio_id
            assert comm.subject == "Scadenza IVA trimestrale"
        # Each client should have its own communication
        result_client_ids = [c.client_id for c in results]
        assert set(result_client_ids) == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_bulk_partial_failure(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Partial failure: some client IDs are invalid, others succeed.

        The service should create drafts for valid clients and return
        partial results with error details for the invalid ones.
        """
        # Simulate a DB-level validation: client 999 does not belong to studio
        valid_client_ids = [1, 2]
        invalid_client_ids = [999]
        all_client_ids = valid_client_ids + invalid_client_ids

        # Mock execute to return client rows only for valid IDs
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[MagicMock(id=cid) for cid in valid_client_ids]))
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await comm_service.create_bulk_drafts(
            db=mock_db,
            studio_id=studio_id,
            client_ids=all_client_ids,
            subject="Avviso importante",
            content="Comunicazione di servizio.",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )

        # Only valid clients get drafts
        created = [r for r in results if isinstance(r, Communication)]
        assert len(created) == 2
        for comm in created:
            assert comm.client_id in valid_client_ids

    @pytest.mark.asyncio
    async def test_bulk_empty_list_raises(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Error: an empty client list must raise ValueError."""
        with pytest.raises(ValueError, match="lista.*client.*vuota"):
            await comm_service.create_bulk_drafts(
                db=mock_db,
                studio_id=studio_id,
                client_ids=[],
                subject="Avviso",
                content="Contenuto.",
                channel=CanaleInvio.EMAIL,
                created_by=1,
            )

    @pytest.mark.asyncio
    async def test_bulk_respects_studio_isolation(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        studio_id,
        other_studio_id,
    ) -> None:
        """Studio isolation: only the requesting studio's clients get drafts.

        When creating bulk drafts, the service must verify that all
        requested client IDs belong to the given studio_id.  Clients
        belonging to a different studio must be excluded.
        """
        # client 1 belongs to studio_id, client 2 belongs to other_studio_id
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[MagicMock(id=1, studio_id=studio_id)]))
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await comm_service.create_bulk_drafts(
            db=mock_db,
            studio_id=studio_id,
            client_ids=[1, 2],
            subject="Avviso",
            content="Contenuto.",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )

        # Only client 1 should have a draft (belongs to studio_id)
        created = [r for r in results if isinstance(r, Communication)]
        assert len(created) == 1
        assert created[0].client_id == 1
