"""DEV-376: Tests for ProcessingRegisterService — GDPR processing register.

Tests cover:
- Create processing activity entry
- List entries with studio isolation
- Update and delete entries
- Legal basis validation
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.processing_register import ProcessingRegister
from app.services.processing_register_service import ProcessingRegisterService


@pytest.fixture
def register_service() -> ProcessingRegisterService:
    return ProcessingRegisterService()


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
def sample_entry(studio_id) -> ProcessingRegister:
    return ProcessingRegister(
        id=uuid4(),
        studio_id=studio_id,
        activity_name="Gestione contabilità clienti",
        purpose="Adempimenti fiscali e contabili",
        legal_basis="Obbligo legale (Art. 6.1.c GDPR)",
        data_categories=["dati_anagrafici", "dati_fiscali"],
        data_subjects="clienti",
        retention_period="10 anni",
        recipients=None,
        third_country_transfers=False,
        notes=None,
    )


class TestProcessingRegisterServiceCreate:
    """Test ProcessingRegisterService.create()."""

    @pytest.mark.asyncio
    async def test_create_entry(
        self,
        register_service: ProcessingRegisterService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Happy path: create a processing activity entry."""
        result = await register_service.create(
            db=mock_db,
            studio_id=studio_id,
            activity_name="Gestione contabilità clienti",
            purpose="Adempimenti fiscali e contabili",
            legal_basis="Obbligo legale (Art. 6.1.c GDPR)",
            data_categories=["dati_anagrafici", "dati_fiscali"],
            data_subjects="clienti",
            retention_period="10 anni",
        )

        assert result.activity_name == "Gestione contabilità clienti"
        assert result.legal_basis == "Obbligo legale (Art. 6.1.c GDPR)"
        assert result.studio_id == studio_id
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_entry_with_legal_basis(
        self,
        register_service: ProcessingRegisterService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Validates legal basis field is stored correctly."""
        legal_bases = [
            "Consenso (Art. 6.1.a GDPR)",
            "Obbligo legale (Art. 6.1.c GDPR)",
            "Interesse legittimo (Art. 6.1.f GDPR)",
        ]

        for basis in legal_bases:
            mock_db.reset_mock()
            result = await register_service.create(
                db=mock_db,
                studio_id=studio_id,
                activity_name="Attività test",
                purpose="Test base giuridica",
                legal_basis=basis,
                data_categories=["dati_anagrafici"],
                data_subjects="clienti",
                retention_period="5 anni",
            )

            assert result.legal_basis == basis


class TestProcessingRegisterServiceList:
    """Test ProcessingRegisterService.list_by_studio()."""

    @pytest.mark.asyncio
    async def test_list_entries_by_studio(
        self,
        register_service: ProcessingRegisterService,
        mock_db: AsyncMock,
        studio_id,
        sample_entry: ProcessingRegister,
    ) -> None:
        """Happy path: list entries filtered by studio (tenant isolation)."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_entry])))
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await register_service.list_by_studio(db=mock_db, studio_id=studio_id)

        assert len(result) == 1
        assert result[0].studio_id == studio_id
        assert result[0].activity_name == "Gestione contabilità clienti"


class TestProcessingRegisterServiceUpdate:
    """Test ProcessingRegisterService.update()."""

    @pytest.mark.asyncio
    async def test_update_entry(
        self,
        register_service: ProcessingRegisterService,
        mock_db: AsyncMock,
        studio_id,
        sample_entry: ProcessingRegister,
    ) -> None:
        """Happy path: update a processing register entry."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_entry)))

        result = await register_service.update(
            db=mock_db,
            entry_id=sample_entry.id,
            studio_id=studio_id,
            activity_name="Gestione contabilità aggiornata",
            retention_period="15 anni",
        )

        assert result is not None


class TestProcessingRegisterServiceDelete:
    """Test ProcessingRegisterService.delete()."""

    @pytest.mark.asyncio
    async def test_delete_entry(
        self,
        register_service: ProcessingRegisterService,
        mock_db: AsyncMock,
        studio_id,
        sample_entry: ProcessingRegister,
    ) -> None:
        """Happy path: delete a processing register entry."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_entry)))

        result = await register_service.delete(
            db=mock_db,
            entry_id=sample_entry.id,
            studio_id=studio_id,
        )

        assert result is True
        mock_db.delete.assert_called_once_with(sample_entry)
