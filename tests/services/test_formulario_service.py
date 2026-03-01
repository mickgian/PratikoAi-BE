"""DEV-431: Tests for FormularioService — list, search, count, get, seed."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.formulario import Formulario, FormularioCategory
from app.services.formulario_service import FormularioService


@pytest.fixture
def service() -> FormularioService:
    return FormularioService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def sample_formulario() -> Formulario:
    return Formulario(
        id=uuid4(),
        code="F24",
        name="Modello F24",
        description="Modello di pagamento unificato per imposte, contributi e premi",
        category=FormularioCategory.VERSAMENTI,
        issuing_authority="Agenzia delle Entrate",
        is_active=True,
    )


@pytest.fixture
def sample_formulari() -> list[Formulario]:
    return [
        Formulario(
            id=uuid4(),
            code="F24",
            name="Modello F24",
            description="Modello di pagamento unificato",
            category=FormularioCategory.VERSAMENTI,
            issuing_authority="Agenzia delle Entrate",
            is_active=True,
        ),
        Formulario(
            id=uuid4(),
            code="CU",
            name="Certificazione Unica",
            description="Certificazione dei redditi",
            category=FormularioCategory.DICHIARAZIONI,
            issuing_authority="Agenzia delle Entrate",
            is_active=True,
        ),
        Formulario(
            id=uuid4(),
            code="770",
            name="Modello 770",
            description="Dichiarazione dei sostituti d'imposta",
            category=FormularioCategory.DICHIARAZIONI,
            issuing_authority="Agenzia delle Entrate",
            is_active=True,
        ),
    ]


class TestFormularioServiceList:
    """Test FormularioService.list_formulari()."""

    @pytest.mark.asyncio
    async def test_list_empty(self, service: FormularioService, mock_db: AsyncMock) -> None:
        """Happy path: empty database returns empty list."""
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        )

        result = await service.list_formulari(db=mock_db)

        assert result == []
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_with_formulari(
        self,
        service: FormularioService,
        mock_db: AsyncMock,
        sample_formulari: list[Formulario],
    ) -> None:
        """Happy path: returns all active formulari."""
        mock_db.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=sample_formulari)))
            )
        )

        result = await service.list_formulari(db=mock_db)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_with_category_filter(
        self,
        service: FormularioService,
        mock_db: AsyncMock,
        sample_formulari: list[Formulario],
    ) -> None:
        """Happy path: filter by category returns matching formulari."""
        dichiarazioni_only = [f for f in sample_formulari if f.category == FormularioCategory.DICHIARAZIONI]
        mock_db.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=dichiarazioni_only)))
            )
        )

        result = await service.list_formulari(db=mock_db, category=FormularioCategory.DICHIARAZIONI)

        assert len(result) == 2
        for f in result:
            assert f.category == FormularioCategory.DICHIARAZIONI

    @pytest.mark.asyncio
    async def test_list_with_search(
        self,
        service: FormularioService,
        mock_db: AsyncMock,
        sample_formulario: Formulario,
    ) -> None:
        """Happy path: text search matches name, code, or description."""
        mock_db.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_formulario])))
            )
        )

        result = await service.list_formulari(db=mock_db, search="F24")

        assert len(result) == 1
        assert result[0].code == "F24"


class TestFormularioServiceCount:
    """Test FormularioService.count_formulari()."""

    @pytest.mark.asyncio
    async def test_count_all(self, service: FormularioService, mock_db: AsyncMock) -> None:
        """Happy path: count all active formulari."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=7)))

        result = await service.count_formulari(db=mock_db)

        assert result == 7

    @pytest.mark.asyncio
    async def test_count_by_category(self, service: FormularioService, mock_db: AsyncMock) -> None:
        """Happy path: count formulari filtered by category."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=3)))

        result = await service.count_formulari(db=mock_db, category=FormularioCategory.DICHIARAZIONI)

        assert result == 3


class TestFormularioServiceGet:
    """Test FormularioService.get_formulario()."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        service: FormularioService,
        mock_db: AsyncMock,
        sample_formulario: Formulario,
    ) -> None:
        """Happy path: retrieve existing formulario by ID."""
        mock_db.get = AsyncMock(return_value=sample_formulario)

        result = await service.get_formulario(db=mock_db, formulario_id=sample_formulario.id)

        assert result is not None
        assert result.id == sample_formulario.id
        assert result.code == "F24"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service: FormularioService, mock_db: AsyncMock) -> None:
        """Error: non-existent formulario returns None."""
        mock_db.get = AsyncMock(return_value=None)

        result = await service.get_formulario(db=mock_db, formulario_id=uuid4())

        assert result is None


class TestFormularioServiceSeed:
    """Test FormularioService.seed_formulari()."""

    @pytest.mark.asyncio
    async def test_seed_creates_records(self, service: FormularioService, mock_db: AsyncMock) -> None:
        """Happy path: seed inserts all default formulari into empty DB."""
        # All lookups return None (no existing records)
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        created = await service.seed_formulari(db=mock_db)

        assert created == 7
        assert mock_db.add.call_count == 7
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_seed_skips_existing(
        self,
        service: FormularioService,
        mock_db: AsyncMock,
        sample_formulario: Formulario,
    ) -> None:
        """Edge case: seed skips already-existing formulari."""
        # First lookup returns existing, rest return None
        mock_db.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=sample_formulario)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            ]
        )

        created = await service.seed_formulari(db=mock_db)

        assert created == 6
        assert mock_db.add.call_count == 6

    @pytest.mark.asyncio
    async def test_seed_no_duplicates(
        self,
        service: FormularioService,
        mock_db: AsyncMock,
        sample_formulario: Formulario,
    ) -> None:
        """Edge case: seed with all records existing creates nothing."""
        # All lookups return an existing record
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_formulario))
        )

        created = await service.seed_formulari(db=mock_db)

        assert created == 0
        mock_db.add.assert_not_called()
        mock_db.flush.assert_not_awaited()
