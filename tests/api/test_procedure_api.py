"""Tests for Procedura API endpoints (DEV-342).

TDD: Tests written FIRST before implementation.
Tests procedure listing, lookup by code, progress tracking,
step advancement, and user progress listing.

Endpoints tested:
- GET  /procedure                          (list active procedures)
- GET  /procedure/{code}                   (get by code)
- POST /procedure/progress                 (start progress)
- POST /procedure/progress/{id}/advance    (advance step)
- GET  /procedure/progress                 (list user progress)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def studio_id() -> UUID:
    """Fixed studio UUID for tenant isolation."""
    return uuid4()


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock async database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def procedura_id() -> UUID:
    """Fixed procedure UUID."""
    return uuid4()


@pytest.fixture
def progress_id() -> UUID:
    """Fixed progress UUID."""
    return uuid4()


@pytest.fixture
def sample_procedura(procedura_id: UUID) -> MagicMock:
    """Return a mock Procedura object."""
    proc = MagicMock()
    proc.id = procedura_id
    proc.code = "APERTURA_PIVA"
    proc.title = "Apertura Partita IVA"
    proc.description = "Procedura guidata per l'apertura di una nuova Partita IVA."
    proc.category = "fiscale"
    proc.steps = [
        {"title": "Raccolta documenti", "checklist": ["Documento identita'", "Codice Fiscale"]},
        {"title": "Compilazione modulo AA9/12", "checklist": ["Dati anagrafici", "Codice ATECO"]},
        {"title": "Invio telematico", "checklist": ["Verifica dati", "Invio"]},
    ]
    proc.estimated_time_minutes = 60
    proc.version = 1
    proc.is_active = True
    proc.last_updated = None
    proc.created_at = datetime.now(UTC)
    proc.updated_at = None
    return proc


@pytest.fixture
def sample_procedura_list(procedura_id: UUID) -> list[MagicMock]:
    """Return a list of mock Procedura objects."""
    procs = []
    codes = [
        ("APERTURA_PIVA", "Apertura Partita IVA", "fiscale"),
        ("ASSUNZIONE_DIPENDENTE", "Assunzione Dipendente", "lavoro"),
        ("COSTITUZIONE_SRL", "Costituzione S.r.l.", "societario"),
    ]
    for i, (code, title, category) in enumerate(codes):
        proc = MagicMock()
        proc.id = uuid4() if i > 0 else procedura_id
        proc.code = code
        proc.title = title
        proc.description = f"Procedura per {title.lower()}."
        proc.category = category
        proc.steps = [{"title": f"Step {j + 1}"} for j in range(3)]
        proc.estimated_time_minutes = 30 + i * 15
        proc.version = 1
        proc.is_active = True
        proc.last_updated = None
        proc.created_at = datetime.now(UTC)
        proc.updated_at = None
        procs.append(proc)
    return procs


@pytest.fixture
def sample_progress(studio_id: UUID, procedura_id: UUID, progress_id: UUID) -> MagicMock:
    """Return a mock ProceduraProgress object."""
    progress = MagicMock()
    progress.id = progress_id
    progress.user_id = 1
    progress.studio_id = studio_id
    progress.procedura_id = procedura_id
    progress.client_id = None
    progress.current_step = 0
    progress.completed_steps = []
    progress.notes = None
    progress.started_at = datetime.now(UTC)
    progress.completed_at = None
    return progress


@pytest.fixture
def sample_advanced_progress(studio_id: UUID, procedura_id: UUID, progress_id: UUID) -> MagicMock:
    """Return a mock ProceduraProgress after step advancement."""
    progress = MagicMock()
    progress.id = progress_id
    progress.user_id = 1
    progress.studio_id = studio_id
    progress.procedura_id = procedura_id
    progress.client_id = None
    progress.current_step = 1
    progress.completed_steps = [0]
    progress.notes = None
    progress.started_at = datetime.now(UTC)
    progress.completed_at = None
    return progress


# ---------------------------------------------------------------------------
# GET /procedure — List active procedures
# ---------------------------------------------------------------------------


class TestListProcedure:
    """Tests for GET /procedure endpoint."""

    @pytest.mark.asyncio
    async def test_list_procedures_success(
        self, mock_db: AsyncMock, studio_id: UUID, sample_procedura_list: list[MagicMock]
    ) -> None:
        """Happy path: returns list of active procedures."""
        from app.api.v1.procedure import list_procedure

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.list_active = AsyncMock(return_value=sample_procedura_list)
            result = await list_procedure(category=None, db=mock_db)

        assert len(result) == 3
        mock_svc.list_active.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_procedures_with_category_filter(
        self, mock_db: AsyncMock, sample_procedura_list: list[MagicMock]
    ) -> None:
        """Happy path: filter by category."""
        from app.api.v1.procedure import list_procedure

        fiscal_only = [p for p in sample_procedura_list if p.category == "fiscale"]

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.list_active = AsyncMock(return_value=fiscal_only)
            result = await list_procedure(category="fiscale", db=mock_db)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_procedures_empty(self, mock_db: AsyncMock) -> None:
        """Edge case: no active procedures returns empty list."""
        from app.api.v1.procedure import list_procedure

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.list_active = AsyncMock(return_value=[])
            result = await list_procedure(category=None, db=mock_db)

        assert result == []


# ---------------------------------------------------------------------------
# GET /procedure/{code} — Get by code
# ---------------------------------------------------------------------------


class TestGetProceduraByCode:
    """Tests for GET /procedure/{code} endpoint."""

    @pytest.mark.asyncio
    async def test_get_by_code_success(self, mock_db: AsyncMock, sample_procedura: MagicMock) -> None:
        """Happy path: returns procedure when code matches."""
        from app.api.v1.procedure import get_procedura_by_code

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.get_by_code = AsyncMock(return_value=sample_procedura)
            result = await get_procedura_by_code(code="APERTURA_PIVA", db=mock_db)

        assert result.code == "APERTURA_PIVA"
        assert result.title == "Apertura Partita IVA"
        assert len(result.steps) == 3
        mock_svc.get_by_code.assert_awaited_once_with(mock_db, code="APERTURA_PIVA")

    @pytest.mark.asyncio
    async def test_get_by_code_not_found_returns_404(self, mock_db: AsyncMock) -> None:
        """Error case: nonexistent code raises 404."""
        from app.api.v1.procedure import get_procedura_by_code

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.get_by_code = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await get_procedura_by_code(code="NON_ESISTE", db=mock_db)

        assert exc_info.value.status_code == 404
        assert "non trovata" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_by_code_returns_steps_structure(self, mock_db: AsyncMock, sample_procedura: MagicMock) -> None:
        """Edge case: verify steps JSONB is correctly returned."""
        from app.api.v1.procedure import get_procedura_by_code

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.get_by_code = AsyncMock(return_value=sample_procedura)
            result = await get_procedura_by_code(code="APERTURA_PIVA", db=mock_db)

        assert isinstance(result.steps, list)
        assert len(result.steps) == 3
        assert result.steps[0]["title"] == "Raccolta documenti"


# ---------------------------------------------------------------------------
# POST /procedure/progress — Start progress
# ---------------------------------------------------------------------------


class TestStartProgress:
    """Tests for POST /procedure/progress endpoint."""

    @pytest.mark.asyncio
    async def test_start_progress_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        procedura_id: UUID,
        sample_progress: MagicMock,
    ) -> None:
        """Happy path: starts progress tracking for user/procedure pair."""
        from app.api.v1.procedure import start_progress
        from app.schemas.procedura import ProceduraProgressCreate

        body = ProceduraProgressCreate(procedura_id=procedura_id)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.start_progress = AsyncMock(return_value=sample_progress)
            result = await start_progress(body=body, studio_id=studio_id, user_id=1, db=mock_db)

        assert result.user_id == 1
        assert result.procedura_id == procedura_id
        assert result.current_step == 0
        assert result.completed_steps == []
        mock_svc.start_progress.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_progress_duplicate_returns_400(
        self, mock_db: AsyncMock, studio_id: UUID, procedura_id: UUID
    ) -> None:
        """Error case: duplicate active progress raises 400."""
        from app.api.v1.procedure import start_progress
        from app.schemas.procedura import ProceduraProgressCreate

        body = ProceduraProgressCreate(procedura_id=procedura_id)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.start_progress = AsyncMock(
                side_effect=ValueError("Il progresso per la procedura e' gia' esistente per l'utente 1.")
            )
            with pytest.raises(HTTPException) as exc_info:
                await start_progress(body=body, studio_id=studio_id, user_id=1, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "progresso" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_start_progress_with_client_id(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        procedura_id: UUID,
        sample_progress: MagicMock,
    ) -> None:
        """Edge case: progress linked to a specific client."""
        from app.api.v1.procedure import start_progress
        from app.schemas.procedura import ProceduraProgressCreate

        sample_progress.client_id = 42
        body = ProceduraProgressCreate(procedura_id=procedura_id, client_id=42)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.start_progress = AsyncMock(return_value=sample_progress)
            result = await start_progress(body=body, studio_id=studio_id, user_id=1, db=mock_db)

        assert result.client_id == 42
        call_kwargs = mock_svc.start_progress.call_args.kwargs
        assert call_kwargs["client_id"] == 42


# ---------------------------------------------------------------------------
# POST /procedure/progress/{id}/advance — Advance step
# ---------------------------------------------------------------------------


class TestAdvanceStep:
    """Tests for POST /procedure/progress/{id}/advance endpoint."""

    @pytest.mark.asyncio
    async def test_advance_step_success(
        self,
        mock_db: AsyncMock,
        progress_id: UUID,
        sample_advanced_progress: MagicMock,
    ) -> None:
        """Happy path: advances from step 0 to step 1."""
        from app.api.v1.procedure import advance_step

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.advance_step = AsyncMock(return_value=sample_advanced_progress)
            result = await advance_step(progress_id=progress_id, db=mock_db)

        assert result.current_step == 1
        assert 0 in result.completed_steps
        mock_svc.advance_step.assert_awaited_once_with(mock_db, progress_id=progress_id)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_advance_step_not_found_returns_404(self, mock_db: AsyncMock) -> None:
        """Error case: nonexistent progress raises 404."""
        from app.api.v1.procedure import advance_step

        fake_id = uuid4()

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.advance_step = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await advance_step(progress_id=fake_id, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_advance_step_completes_procedure(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        procedura_id: UUID,
        progress_id: UUID,
    ) -> None:
        """Edge case: advancing last step marks procedure as completed."""
        from app.api.v1.procedure import advance_step

        completed_progress = MagicMock()
        completed_progress.id = progress_id
        completed_progress.user_id = 1
        completed_progress.studio_id = studio_id
        completed_progress.procedura_id = procedura_id
        completed_progress.client_id = None
        completed_progress.current_step = 2
        completed_progress.completed_steps = [0, 1, 2]
        completed_progress.notes = None
        completed_progress.started_at = datetime.now(UTC)
        completed_progress.completed_at = datetime.now(UTC)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.advance_step = AsyncMock(return_value=completed_progress)
            result = await advance_step(progress_id=progress_id, db=mock_db)

        assert result.completed_at is not None
        assert len(result.completed_steps) == 3


# ---------------------------------------------------------------------------
# GET /procedure/progress — List user progress
# ---------------------------------------------------------------------------


class TestListUserProgress:
    """Tests for GET /procedure/progress endpoint."""

    @pytest.mark.asyncio
    async def test_list_user_progress_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        sample_progress: MagicMock,
    ) -> None:
        """Happy path: returns list of user's progress records."""
        from app.api.v1.procedure import list_user_progress

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.list_user_progress = AsyncMock(return_value=[sample_progress])
            result = await list_user_progress(studio_id=studio_id, user_id=1, db=mock_db)

        assert len(result) == 1
        assert result[0].user_id == 1
        mock_svc.list_user_progress.assert_awaited_once_with(mock_db, user_id=1, studio_id=studio_id)

    @pytest.mark.asyncio
    async def test_list_user_progress_empty(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Edge case: user has no progress records."""
        from app.api.v1.procedure import list_user_progress

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.list_user_progress = AsyncMock(return_value=[])
            result = await list_user_progress(studio_id=studio_id, user_id=1, db=mock_db)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_user_progress_multiple_records(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Edge case: user has multiple progress records across procedures."""
        from app.api.v1.procedure import list_user_progress

        prog1 = MagicMock()
        prog1.id = uuid4()
        prog1.user_id = 1
        prog1.studio_id = studio_id
        prog1.procedura_id = uuid4()
        prog1.client_id = None
        prog1.current_step = 2
        prog1.completed_steps = [0, 1]
        prog1.notes = None
        prog1.started_at = datetime.now(UTC)
        prog1.completed_at = None

        prog2 = MagicMock()
        prog2.id = uuid4()
        prog2.user_id = 1
        prog2.studio_id = studio_id
        prog2.procedura_id = uuid4()
        prog2.client_id = 5
        prog2.current_step = 0
        prog2.completed_steps = []
        prog2.notes = "Appena iniziato"
        prog2.started_at = datetime.now(UTC)
        prog2.completed_at = None

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.list_user_progress = AsyncMock(return_value=[prog1, prog2])
            result = await list_user_progress(studio_id=studio_id, user_id=1, db=mock_db)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# PUT /procedure/progress/{id}/checklist — Update checklist
# ---------------------------------------------------------------------------


class TestUpdateChecklistItem:
    """Tests for PUT /procedure/progress/{id}/checklist endpoint."""

    @pytest.mark.asyncio
    async def test_update_checklist_success(
        self,
        mock_db: AsyncMock,
        progress_id: UUID,
        sample_progress: MagicMock,
    ) -> None:
        """Happy path: mark checklist item as completed."""
        from app.api.v1.procedure import update_checklist_item
        from app.schemas.procedura import ChecklistItemUpdate

        body = ChecklistItemUpdate(step_index=0, item_index=0, completed=True)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.update_checklist_item = AsyncMock(return_value=sample_progress)
            result = await update_checklist_item(progress_id=progress_id, body=body, db=mock_db)

        assert result.id == progress_id
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_checklist_invalid_index_returns_400(
        self,
        mock_db: AsyncMock,
        progress_id: UUID,
    ) -> None:
        """Error case: invalid step/item index raises 400."""
        from app.api.v1.procedure import update_checklist_item
        from app.schemas.procedura import ChecklistItemUpdate

        body = ChecklistItemUpdate(step_index=99, item_index=0, completed=True)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.update_checklist_item = AsyncMock(side_effect=ValueError("Indice dello step non valido."))
            with pytest.raises(HTTPException) as exc_info:
                await update_checklist_item(progress_id=progress_id, body=body, db=mock_db)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_checklist_not_found_returns_404(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Error case: nonexistent progress raises 404."""
        from app.api.v1.procedure import update_checklist_item
        from app.schemas.procedura import ChecklistItemUpdate

        body = ChecklistItemUpdate(step_index=0, item_index=0, completed=True)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.update_checklist_item = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await update_checklist_item(progress_id=uuid4(), body=body, db=mock_db)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# PUT /procedure/progress/{id}/notes — Update notes
# ---------------------------------------------------------------------------


class TestUpdateNotes:
    """Tests for PUT /procedure/progress/{id}/notes endpoint."""

    @pytest.mark.asyncio
    async def test_update_notes_success(
        self,
        mock_db: AsyncMock,
        progress_id: UUID,
        sample_progress: MagicMock,
    ) -> None:
        """Happy path: update progress notes."""
        from app.api.v1.procedure import update_notes
        from app.schemas.procedura import ProceduraNotesUpdate

        sample_progress.notes = "Note aggiornate"
        body = ProceduraNotesUpdate(notes="Note aggiornate")

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.update_notes = AsyncMock(return_value=sample_progress)
            result = await update_notes(progress_id=progress_id, body=body, db=mock_db)

        assert result.notes == "Note aggiornate"
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_notes_not_found_returns_404(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Error case: nonexistent progress raises 404."""
        from app.api.v1.procedure import update_notes
        from app.schemas.procedura import ProceduraNotesUpdate

        body = ProceduraNotesUpdate(notes="Qualcosa")

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.update_notes = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await update_notes(progress_id=uuid4(), body=body, db=mock_db)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# PUT /procedure/progress/{id}/document — Update document status
# ---------------------------------------------------------------------------


class TestUpdateDocumentStatus:
    """Tests for PUT /procedure/progress/{id}/document endpoint."""

    @pytest.mark.asyncio
    async def test_update_document_status_success(
        self,
        mock_db: AsyncMock,
        progress_id: UUID,
        sample_progress: MagicMock,
    ) -> None:
        """Happy path: mark a document as verified."""
        from app.api.v1.procedure import update_document_status
        from app.schemas.procedura import DocumentChecklistUpdate

        body = DocumentChecklistUpdate(document_name="Documento identita'", verified=True)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.update_document_status = AsyncMock(return_value=sample_progress)
            result = await update_document_status(progress_id=progress_id, body=body, db=mock_db)

        assert result.id == progress_id
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_document_status_invalid_doc_returns_400(
        self,
        mock_db: AsyncMock,
        progress_id: UUID,
    ) -> None:
        """Error case: unknown document name raises 400."""
        from app.api.v1.procedure import update_document_status
        from app.schemas.procedura import DocumentChecklistUpdate

        body = DocumentChecklistUpdate(document_name="NonEsiste", verified=True)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.update_document_status = AsyncMock(
                side_effect=ValueError("Documento non presente nella procedura.")
            )
            with pytest.raises(HTTPException) as exc_info:
                await update_document_status(progress_id=progress_id, body=body, db=mock_db)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_document_status_not_found_returns_404(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Error case: nonexistent progress raises 404."""
        from app.api.v1.procedure import update_document_status
        from app.schemas.procedura import DocumentChecklistUpdate

        body = DocumentChecklistUpdate(document_name="Doc", verified=True)

        with patch("app.api.v1.procedure.procedura_service") as mock_svc:
            mock_svc.update_document_status = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await update_document_status(progress_id=uuid4(), body=body, db=mock_db)

        assert exc_info.value.status_code == 404
