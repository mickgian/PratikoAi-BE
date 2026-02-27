"""DEV-383: Tests for DeadlineMatchingService — Client-Deadline matching.

Tests cover:
- Happy path: match deadline to clients based on type criteria
- FISCALE deadline matches all active clients
- CONTRIBUTIVO deadline matches only clients with employees
- SOCIETARIO deadline matches only societa clients
- ADEMPIMENTO deadline matches all active clients
- Edge case: no clients match criteria
- Edge case: deadline not found raises ValueError
- Duplicate prevention: skip already-assigned client-deadline pairs
- Creates ClientDeadline records correctly
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.deadline import ClientDeadline, Deadline, DeadlineSource, DeadlineType
from app.services.deadline_matching_service import DeadlineMatchingService


@pytest.fixture
def matching_service() -> DeadlineMatchingService:
    return DeadlineMatchingService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def fiscale_deadline() -> Deadline:
    return Deadline(
        id=uuid4(),
        title="Versamento IVA trimestrale",
        description="Versamento IVA trimestrale per regime ordinario.",
        deadline_type=DeadlineType.FISCALE,
        source=DeadlineSource.REGULATORY,
        due_date=date(2026, 3, 16),
        is_active=True,
    )


@pytest.fixture
def contributivo_deadline() -> Deadline:
    return Deadline(
        id=uuid4(),
        title="Contributi INPS dipendenti",
        description="Versamento contributi INPS per dipendenti.",
        deadline_type=DeadlineType.CONTRIBUTIVO,
        source=DeadlineSource.REGULATORY,
        due_date=date(2026, 3, 16),
        is_active=True,
    )


@pytest.fixture
def societario_deadline() -> Deadline:
    return Deadline(
        id=uuid4(),
        title="Approvazione bilancio",
        description="Assemblea ordinaria per approvazione bilancio.",
        deadline_type=DeadlineType.SOCIETARIO,
        source=DeadlineSource.REGULATORY,
        due_date=date(2026, 4, 30),
        is_active=True,
    )


@pytest.fixture
def adempimento_deadline() -> Deadline:
    return Deadline(
        id=uuid4(),
        title="Comunicazione annuale",
        description="Comunicazione annuale obbligatoria.",
        deadline_type=DeadlineType.ADEMPIMENTO,
        source=DeadlineSource.REGULATORY,
        due_date=date(2026, 2, 28),
        is_active=True,
    )


def _make_client(
    client_id: int,
    studio_id,
    tipo_cliente: str = "persona_fisica",
    stato_cliente: str = "attivo",
    n_dipendenti: int = 0,
) -> tuple[MagicMock, MagicMock]:
    """Helper to create a mock client + profile pair."""
    client = MagicMock()
    client.id = client_id
    client.studio_id = studio_id
    client.tipo_cliente = tipo_cliente
    client.stato_cliente = stato_cliente
    client.deleted_at = None

    profile = MagicMock()
    profile.client_id = client_id
    profile.n_dipendenti = n_dipendenti

    return client, profile


def _not_existing_result() -> MagicMock:
    """Create a mock result for 'no existing assignment' queries."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    return result


def _mock_execute_for_clients_and_checks(
    mock_db: AsyncMock,
    client_profile_pairs: list,
    num_eligible: int | None = None,
) -> None:
    """Configure mock_db.execute for the full flow.

    The service calls db.execute multiple times:
    1. First call: _fetch_studio_clients (returns .all())
    2. Subsequent calls: _check_existing_assignment per eligible client (returns .scalar_one_or_none())

    Args:
        mock_db: The mock session.
        client_profile_pairs: List of (client, profile) tuples for the fetch query.
        num_eligible: Number of eligible clients that will have their duplicates checked.
                     If None, defaults to len(client_profile_pairs).
    """
    if num_eligible is None:
        num_eligible = len(client_profile_pairs)

    side_effects = []

    # First call: fetch clients
    clients_result = MagicMock()
    clients_result.all = MagicMock(return_value=client_profile_pairs)
    side_effects.append(clients_result)

    # Subsequent calls: duplicate check per eligible client (all return "not found")
    for _ in range(num_eligible):
        side_effects.append(_not_existing_result())

    mock_db.execute = AsyncMock(side_effect=side_effects)


class TestMatchFiscaleDeadline:
    """FISCALE deadlines should match all active clients."""

    @pytest.mark.asyncio
    async def test_fiscale_matches_all_active_clients(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        fiscale_deadline: Deadline,
    ) -> None:
        """Happy path: FISCALE deadline matches all active clients."""
        mock_db.get = AsyncMock(return_value=fiscale_deadline)

        c1, p1 = _make_client(1, studio_id, tipo_cliente="persona_fisica")
        c2, p2 = _make_client(2, studio_id, tipo_cliente="societa")
        c3, p3 = _make_client(3, studio_id, tipo_cliente="ditta_individuale")
        _mock_execute_for_clients_and_checks(mock_db, [(c1, p1), (c2, p2), (c3, p3)])

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=fiscale_deadline.id,
            studio_id=studio_id,
        )

        assert len(results) == 3
        client_ids = {r.client_id for r in results}
        assert client_ids == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_fiscale_creates_client_deadline_records(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        fiscale_deadline: Deadline,
    ) -> None:
        """Verify ClientDeadline records are created with correct fields."""
        mock_db.get = AsyncMock(return_value=fiscale_deadline)

        c1, p1 = _make_client(1, studio_id)
        _mock_execute_for_clients_and_checks(mock_db, [(c1, p1)])

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=fiscale_deadline.id,
            studio_id=studio_id,
        )

        assert len(results) == 1
        cd = results[0]
        assert cd.client_id == 1
        assert cd.deadline_id == fiscale_deadline.id
        assert cd.studio_id == studio_id
        assert cd.is_completed is False
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()


class TestMatchContributivoDeadline:
    """CONTRIBUTIVO deadlines should match only clients with employees."""

    @pytest.mark.asyncio
    async def test_contributivo_matches_clients_with_employees(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        contributivo_deadline: Deadline,
    ) -> None:
        """Happy path: CONTRIBUTIVO matches only clients with n_dipendenti > 0."""
        mock_db.get = AsyncMock(return_value=contributivo_deadline)

        c1, p1 = _make_client(1, studio_id, n_dipendenti=5)
        c2, p2 = _make_client(2, studio_id, n_dipendenti=0)
        c3, p3 = _make_client(3, studio_id, n_dipendenti=12)
        # Only 2 eligible (c1 and c3), c2 is filtered out
        _mock_execute_for_clients_and_checks(mock_db, [(c1, p1), (c2, p2), (c3, p3)], num_eligible=2)

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=contributivo_deadline.id,
            studio_id=studio_id,
        )

        assert len(results) == 2
        client_ids = {r.client_id for r in results}
        assert client_ids == {1, 3}

    @pytest.mark.asyncio
    async def test_contributivo_no_clients_with_employees(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        contributivo_deadline: Deadline,
    ) -> None:
        """Edge case: no clients have employees, empty result."""
        mock_db.get = AsyncMock(return_value=contributivo_deadline)

        c1, p1 = _make_client(1, studio_id, n_dipendenti=0)
        c2, p2 = _make_client(2, studio_id, n_dipendenti=0)
        _mock_execute_for_clients_and_checks(mock_db, [(c1, p1), (c2, p2)], num_eligible=0)

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=contributivo_deadline.id,
            studio_id=studio_id,
        )

        assert results == []


class TestMatchSocietarioDeadline:
    """SOCIETARIO deadlines should match only societa-type clients."""

    @pytest.mark.asyncio
    async def test_societario_matches_societa_clients(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        societario_deadline: Deadline,
    ) -> None:
        """Happy path: SOCIETARIO matches only tipo_cliente=SOCIETA."""
        mock_db.get = AsyncMock(return_value=societario_deadline)

        c1, p1 = _make_client(1, studio_id, tipo_cliente="societa")
        c2, p2 = _make_client(2, studio_id, tipo_cliente="persona_fisica")
        c3, p3 = _make_client(3, studio_id, tipo_cliente="societa")
        # Only 2 eligible (c1 and c3)
        _mock_execute_for_clients_and_checks(mock_db, [(c1, p1), (c2, p2), (c3, p3)], num_eligible=2)

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=societario_deadline.id,
            studio_id=studio_id,
        )

        assert len(results) == 2
        client_ids = {r.client_id for r in results}
        assert client_ids == {1, 3}

    @pytest.mark.asyncio
    async def test_societario_no_societa_clients(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        societario_deadline: Deadline,
    ) -> None:
        """Edge case: no societa clients, empty result."""
        mock_db.get = AsyncMock(return_value=societario_deadline)

        c1, p1 = _make_client(1, studio_id, tipo_cliente="persona_fisica")
        c2, p2 = _make_client(2, studio_id, tipo_cliente="ditta_individuale")
        _mock_execute_for_clients_and_checks(mock_db, [(c1, p1), (c2, p2)], num_eligible=0)

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=societario_deadline.id,
            studio_id=studio_id,
        )

        assert results == []


class TestMatchAdempimentoDeadline:
    """ADEMPIMENTO deadlines should match all active clients."""

    @pytest.mark.asyncio
    async def test_adempimento_matches_all_active_clients(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        adempimento_deadline: Deadline,
    ) -> None:
        """Happy path: ADEMPIMENTO matches all active clients like FISCALE."""
        mock_db.get = AsyncMock(return_value=adempimento_deadline)

        c1, p1 = _make_client(1, studio_id)
        c2, p2 = _make_client(2, studio_id)
        _mock_execute_for_clients_and_checks(mock_db, [(c1, p1), (c2, p2)])

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=adempimento_deadline.id,
            studio_id=studio_id,
        )

        assert len(results) == 2


class TestMatchDeadlineEdgeCases:
    """Edge cases for deadline matching."""

    @pytest.mark.asyncio
    async def test_deadline_not_found_raises(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Error: non-existent deadline raises ValueError."""
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="non trovata"):
            await matching_service.match_deadline_to_clients(
                db=mock_db,
                deadline_id=uuid4(),
                studio_id=studio_id,
            )

    @pytest.mark.asyncio
    async def test_no_clients_in_studio(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        fiscale_deadline: Deadline,
    ) -> None:
        """Edge case: studio has no clients, returns empty list."""
        mock_db.get = AsyncMock(return_value=fiscale_deadline)
        _mock_execute_for_clients_and_checks(mock_db, [])

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=fiscale_deadline.id,
            studio_id=studio_id,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_skip_already_assigned_clients(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        fiscale_deadline: Deadline,
    ) -> None:
        """Duplicate prevention: skip clients already assigned to this deadline."""
        mock_db.get = AsyncMock(return_value=fiscale_deadline)

        c1, p1 = _make_client(1, studio_id)
        c2, p2 = _make_client(2, studio_id)

        existing_cd = ClientDeadline(
            client_id=1,
            deadline_id=fiscale_deadline.id,
            studio_id=studio_id,
        )

        side_effects = []

        # First call: fetch clients
        clients_result = MagicMock()
        clients_result.all = MagicMock(return_value=[(c1, p1), (c2, p2)])
        side_effects.append(clients_result)

        # Second call: check existing for client 1 (already exists)
        existing_result = MagicMock()
        existing_result.scalar_one_or_none = MagicMock(return_value=existing_cd)
        side_effects.append(existing_result)

        # Third call: check existing for client 2 (not exists)
        side_effects.append(_not_existing_result())

        mock_db.execute = AsyncMock(side_effect=side_effects)

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=fiscale_deadline.id,
            studio_id=studio_id,
        )

        # Only client 2 should be newly assigned
        assert len(results) == 1
        assert results[0].client_id == 2

    @pytest.mark.asyncio
    async def test_client_without_profile_still_matches_fiscale(
        self,
        matching_service: DeadlineMatchingService,
        mock_db: AsyncMock,
        studio_id,
        fiscale_deadline: Deadline,
    ) -> None:
        """Clients without profiles still match FISCALE/ADEMPIMENTO deadlines."""
        mock_db.get = AsyncMock(return_value=fiscale_deadline)

        client = MagicMock()
        client.id = 1
        client.studio_id = studio_id
        client.tipo_cliente = "persona_fisica"
        client.stato_cliente = "attivo"
        client.deleted_at = None
        # Profile is None
        _mock_execute_for_clients_and_checks(mock_db, [(client, None)], num_eligible=1)

        results = await matching_service.match_deadline_to_clients(
            db=mock_db,
            deadline_id=fiscale_deadline.id,
            studio_id=studio_id,
        )

        assert len(results) == 1
        assert results[0].client_id == 1
