"""Unit tests for TaskGeneratorService.

Tests the automatic task generation from expert feedback, including:
- Task ID generation (scanning files, incrementing max number)
- Task name generation (truncation, sanitization)
- Markdown formatting
- File operations (append to existing)
- Database operations
- Error handling

Note: The service generates QUERY-XX task IDs (starting from QUERY-08) and writes
to QUERY_ISSUES_ROADMAP.md. It creates its own database session internally.
"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality_analysis import ExpertFeedback, ExpertGeneratedTask, ExpertProfile, FeedbackType
from app.services.task_generator_service import TaskGeneratorService


@pytest.fixture
def task_generator_service():
    """TaskGeneratorService instance.

    Note: The service does NOT accept a db argument - it creates its own
    database session internally using AsyncSessionLocal().
    """
    return TaskGeneratorService()


@pytest.fixture
def sample_feedback():
    """Sample expert feedback record using MagicMock to avoid SQLAlchemy mapper issues."""
    feedback = MagicMock(spec=ExpertFeedback)
    feedback.id = uuid4()
    feedback.query_id = uuid4()
    feedback.expert_id = uuid4()
    feedback.feedback_type = FeedbackType.INCOMPLETE
    feedback.category = None
    feedback.query_text = "Come si calcola l'IVA per il regime forfettario?"
    feedback.original_answer = "Nel regime forfettario non si applica l'IVA."
    feedback.expert_answer = "Nel regime forfettario non si applica l'IVA in fattura, ma..."
    feedback.improvement_suggestions = ["Aggiungere casi specifici"]
    feedback.regulatory_references = ["Art. 1, comma 54-89, L. 190/2014"]
    feedback.confidence_score = 0.9
    feedback.time_spent_seconds = 180
    feedback.complexity_rating = 3
    feedback.additional_details = "La risposta è incompleta perche non tratta i casi specifici."
    feedback.task_creation_attempted = False
    feedback.generated_task_id = None
    feedback.task_creation_success = None
    feedback.task_creation_error = None
    return feedback


@pytest.fixture
def sample_expert():
    """Sample expert profile using MagicMock to avoid SQLAlchemy mapper issues."""
    expert = MagicMock(spec=ExpertProfile)
    expert.id = uuid4()
    expert.user_id = uuid4()
    expert.credentials = ["Dottore Commercialista"]
    expert.credential_types = []
    expert.experience_years = 15
    expert.specializations = ["diritto_tributario"]
    expert.feedback_count = 100
    expert.feedback_accuracy_rate = 0.95
    expert.average_response_time_seconds = 200
    expert.trust_score = 0.92
    expert.is_verified = True
    expert.is_active = True
    return expert


class TestTaskIDGeneration:
    """Tests for task ID generation logic.

    The service queries the database first for max task_id, then falls back to
    file scanning. IDs start from QUERY-08 (01-07 are reserved).
    """

    @pytest.mark.asyncio
    async def test_generate_task_id_no_existing_files(self, task_generator_service):
        """Test task ID generation when no DB records and no files exist (starts from QUERY-08)."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No DB records
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(task_generator_service, "_scan_file_for_max_task_number", return_value=0):
            task_id = await task_generator_service._generate_task_id(mock_session)

            # Starts from QUERY-08 (01-07 are reserved)
            assert task_id == "QUERY-08"

    @pytest.mark.asyncio
    async def test_generate_task_id_with_existing_tasks(self, task_generator_service):
        """Test task ID generation increments from max existing number in file."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No DB records
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock file has QUERY-15
        with patch.object(task_generator_service, "_scan_file_for_max_task_number", return_value=15):
            task_id = await task_generator_service._generate_task_id(mock_session)

            # Should be 15 + 1 = 16
            assert task_id == "QUERY-16"

    @pytest.mark.asyncio
    async def test_generate_task_id_respects_minimum(self, task_generator_service):
        """Test task ID starts from at least QUERY-08 even if file has lower numbers."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No DB records
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock file has only QUERY-03 (which is in reserved range)
        with patch.object(task_generator_service, "_scan_file_for_max_task_number", return_value=3):
            task_id = await task_generator_service._generate_task_id(mock_session)

            # Should still be QUERY-08 (minimum)
            assert task_id == "QUERY-08"

    @pytest.mark.asyncio
    async def test_scan_file_for_max_task_number_file_exists(self, task_generator_service, tmp_path):
        """Test scanning file for task IDs when file exists."""
        # Create temp file with task IDs
        test_file = tmp_path / "test_tasks.md"
        test_file.write_text(
            """
        # Tasks
        - QUERY-10: Task 10
        - QUERY-25: Task 25
        - QUERY-15: Task 15
        """
        )

        max_num = await task_generator_service._scan_file_for_max_task_number(test_file, pattern=r"QUERY-(\d+)")

        assert max_num == 25

    @pytest.mark.asyncio
    async def test_scan_file_for_max_task_number_file_not_exists(self, task_generator_service, tmp_path):
        """Test scanning file returns 0 when file doesn't exist."""
        non_existent_file = tmp_path / "nonexistent.md"

        max_num = await task_generator_service._scan_file_for_max_task_number(
            non_existent_file, pattern=r"QUERY-(\d+)"
        )

        assert max_num == 0

    @pytest.mark.asyncio
    async def test_scan_file_for_max_task_number_no_matches(self, task_generator_service, tmp_path):
        """Test scanning file returns 0 when no task IDs found."""
        test_file = tmp_path / "test_empty.md"
        test_file.write_text("# No tasks here")

        max_num = await task_generator_service._scan_file_for_max_task_number(test_file, pattern=r"QUERY-(\d+)")

        assert max_num == 0


class TestTaskNameGeneration:
    """Tests for task name generation logic."""

    def test_generate_task_name_normal(self, task_generator_service):
        """Test normal task name generation."""
        question = "Come si calcola l'IVA?"
        name = task_generator_service._generate_task_name(question)

        assert name == "COME_SI_CALCOLA_LIVA"
        assert len(name) <= 30

    def test_generate_task_name_truncation(self, task_generator_service):
        """Test task name is truncated to 30 chars."""
        question = "Come si calcola l'IVA per il regime forfettario con partita IVA estera?"
        name = task_generator_service._generate_task_name(question)

        assert len(name) <= 30
        assert name.startswith("COME_SI_CALCOLA")

    def test_generate_task_name_special_characters(self, task_generator_service):
        """Test special characters are removed from task name."""
        question = "Come calcolare l'IVA? (2024)"
        name = task_generator_service._generate_task_name(question)

        # Should have no parentheses or question marks
        assert "(" not in name
        assert ")" not in name
        assert "?" not in name
        assert name == "COME_CALCOLARE_LIVA_2024"

    def test_generate_task_name_empty_after_sanitization(self, task_generator_service):
        """Test fallback name when question sanitizes to empty."""
        question = "???!!!"
        name = task_generator_service._generate_task_name(question)

        assert name == "EXPERT_FEEDBACK_TASK"


class TestMarkdownGeneration:
    """Tests for markdown task generation."""

    def test_create_task_markdown_structure(self, task_generator_service, sample_feedback, sample_expert):
        """Test markdown task contains all required sections."""
        task_id = "QUERY-08"
        task_name = "CALCOLO_IVA"

        markdown = task_generator_service._create_task_markdown(task_id, task_name, sample_feedback, sample_expert)

        # Check required sections
        assert f"### {task_id}: {task_name}" in markdown
        assert "**Priority:** HIGH" in markdown
        assert f"**Source:** Expert Feedback (ID: {sample_feedback.id})" in markdown
        assert f"**Expert:** User {sample_expert.user_id}" in markdown
        assert f"Trust Score: {sample_expert.trust_score:.2f}" in markdown
        assert "**Domanda originale:**" in markdown
        assert sample_feedback.query_text in markdown
        assert "**Risposta fornita (incompleta/errata):**" in markdown
        assert sample_feedback.original_answer in markdown
        assert "**Dettagli aggiuntivi dall'esperto:**" in markdown
        assert sample_feedback.additional_details in markdown
        assert "**Status:**" in markdown
        assert "TODO" in markdown

    def test_create_task_markdown_includes_regulatory_references(
        self, task_generator_service, sample_feedback, sample_expert
    ):
        """Test markdown includes regulatory references when present."""
        sample_feedback.regulatory_references = ["Art. 1, L. 190/2014", "D.L. 119/2018"]

        markdown = task_generator_service._create_task_markdown("QUERY-08", "TASK", sample_feedback, sample_expert)

        assert "**Riferimenti normativi citati dall'esperto:**" in markdown
        assert "Art. 1, L. 190/2014" in markdown
        assert "D.L. 119/2018" in markdown

    def test_create_task_markdown_includes_improvement_suggestions(
        self, task_generator_service, sample_feedback, sample_expert
    ):
        """Test markdown includes improvement suggestions when present."""
        sample_feedback.improvement_suggestions = [
            "Aggiungere casi specifici",
            "Citare normativa aggiornata",
        ]

        markdown = task_generator_service._create_task_markdown("QUERY-08", "TASK", sample_feedback, sample_expert)

        assert "**Suggerimenti per il miglioramento:**" in markdown
        assert "Aggiungere casi specifici" in markdown
        assert "Citare normativa aggiornata" in markdown

    def test_create_task_markdown_feedback_type_translation(
        self, task_generator_service, sample_feedback, sample_expert
    ):
        """Test feedback type is translated to Italian."""
        sample_feedback.feedback_type = MagicMock()
        sample_feedback.feedback_type.value = "incomplete"

        markdown = task_generator_service._create_task_markdown("QUERY-08", "TASK", sample_feedback, sample_expert)

        assert "**Incompleta**" in markdown

        sample_feedback.feedback_type.value = "incorrect"
        markdown = task_generator_service._create_task_markdown("QUERY-08", "TASK", sample_feedback, sample_expert)

        assert "**Errata**" in markdown


class TestTaskGeneration:
    """Tests for end-to-end task generation.

    Note: The service method generate_task_from_feedback takes (feedback_id, expert_id)
    as UUIDs, NOT the actual objects. It creates its own database session and loads
    the objects from the database.
    """

    @pytest.mark.asyncio
    async def test_generate_task_from_feedback_success(
        self, task_generator_service, sample_feedback, sample_expert, tmp_path
    ):
        """Test successful task generation from feedback."""
        # Mock file operations
        task_generator_service.project_root = tmp_path

        # Create docs/tasks/QUERY_ISSUES_ROADMAP.md
        docs_tasks = tmp_path / "docs" / "tasks"
        docs_tasks.mkdir(parents=True)
        roadmap_file = docs_tasks / "QUERY_ISSUES_ROADMAP.md"
        roadmap_file.write_text("# Query Issues Roadmap\n\n")

        # Mock the database session and operations
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=[sample_feedback, sample_expert])
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = Mock()

        # Mock the execute for task ID generation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing tasks in DB
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Create a context manager mock for AsyncSessionLocal
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.task_generator_service.AsyncSessionLocal", return_value=mock_session_ctx):
            task_id = await task_generator_service.generate_task_from_feedback(
                feedback_id=sample_feedback.id, expert_id=sample_expert.id
            )

            assert task_id is not None
            assert task_id.startswith("QUERY-")

            # Verify file was updated
            content = roadmap_file.read_text()
            assert task_id in content
            assert sample_feedback.query_text in content

    @pytest.mark.asyncio
    async def test_generate_task_skips_correct_feedback(self, task_generator_service, sample_feedback, sample_expert):
        """Test task generation is skipped for 'correct' feedback."""
        sample_feedback.feedback_type = MagicMock()
        sample_feedback.feedback_type.value = "correct"

        # Mock the database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=[sample_feedback, sample_expert])
        mock_session.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.task_generator_service.AsyncSessionLocal", return_value=mock_session_ctx):
            task_id = await task_generator_service.generate_task_from_feedback(
                feedback_id=sample_feedback.id, expert_id=sample_expert.id
            )

            assert task_id is None

    @pytest.mark.asyncio
    async def test_generate_task_skips_without_additional_details(
        self, task_generator_service, sample_feedback, sample_expert
    ):
        """Test task generation is skipped without additional_details."""
        sample_feedback.additional_details = None
        sample_feedback.feedback_type = MagicMock()
        sample_feedback.feedback_type.value = "incomplete"

        # Mock the database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=[sample_feedback, sample_expert])
        mock_session.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.task_generator_service.AsyncSessionLocal", return_value=mock_session_ctx):
            task_id = await task_generator_service.generate_task_from_feedback(
                feedback_id=sample_feedback.id, expert_id=sample_expert.id
            )

            assert task_id is None

    @pytest.mark.asyncio
    async def test_generate_task_handles_missing_feedback(self, task_generator_service):
        """Test task generation handles missing feedback record gracefully."""
        # Mock the database session returning None for feedback
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.task_generator_service.AsyncSessionLocal", return_value=mock_session_ctx):
            task_id = await task_generator_service.generate_task_from_feedback(feedback_id=uuid4(), expert_id=uuid4())

            # Should return None without raising
            assert task_id is None

    @pytest.mark.asyncio
    async def test_generate_task_handles_errors_gracefully(
        self, task_generator_service, sample_feedback, sample_expert
    ):
        """Test task generation handles errors without raising exceptions."""
        sample_feedback.feedback_type = MagicMock()
        sample_feedback.feedback_type.value = "incomplete"

        # Mock the database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=[sample_feedback, sample_expert])
        mock_session.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        # Force an error by making _generate_task_id raise
        with (
            patch("app.services.task_generator_service.AsyncSessionLocal", return_value=mock_session_ctx),
            patch.object(task_generator_service, "_generate_task_id", side_effect=Exception("Test error")),
        ):
            task_id = await task_generator_service.generate_task_from_feedback(
                feedback_id=sample_feedback.id, expert_id=sample_expert.id
            )

            # Should return None and not raise
            assert task_id is None


class TestFileOperations:
    """Tests for file operations.

    Note: The service writes to docs/tasks/QUERY_ISSUES_ROADMAP.md.
    If the file doesn't exist, it is created automatically with a header.
    File write failures are handled gracefully (return False, don't raise).
    """

    @pytest.mark.asyncio
    async def test_append_to_file_appends_to_existing_file(self, task_generator_service, tmp_path):
        """Test content is appended to existing file."""
        task_generator_service.project_root = tmp_path
        docs_tasks = tmp_path / "docs" / "tasks"
        docs_tasks.mkdir(parents=True)
        roadmap_file = docs_tasks / "QUERY_ISSUES_ROADMAP.md"

        # Create file with initial content
        roadmap_file.write_text("# Query Issues Roadmap\n\n## Existing Content\n")

        result = await task_generator_service._append_to_file("## New Task\n")

        assert result is True
        content = roadmap_file.read_text()
        assert "# Query Issues Roadmap" in content
        assert "## Existing Content" in content
        assert "## New Task" in content

    @pytest.mark.asyncio
    async def test_append_to_file_preserves_original_content(self, task_generator_service, tmp_path):
        """Test that appending preserves all original content."""
        task_generator_service.project_root = tmp_path
        roadmap_file = tmp_path / "docs" / "tasks" / "QUERY_ISSUES_ROADMAP.md"
        roadmap_file.parent.mkdir(parents=True, exist_ok=True)

        original_content = """# Query Issues Roadmap

## QUERY-01: Reserved Task
Some content here.

## QUERY-07: Last Reserved Task
More content.
"""
        roadmap_file.write_text(original_content)

        result = await task_generator_service._append_to_file("\n## QUERY-08: New Task\nNew content.\n")

        assert result is True
        content = roadmap_file.read_text()
        # Original content preserved
        assert "QUERY-01: Reserved Task" in content
        assert "QUERY-07: Last Reserved Task" in content
        # New content appended
        assert "QUERY-08: New Task" in content

    @pytest.mark.asyncio
    async def test_append_to_file_creates_file_if_missing(self, task_generator_service, tmp_path):
        """Test that file is auto-created with header if it doesn't exist."""
        task_generator_service.project_root = tmp_path
        roadmap_file = tmp_path / "docs" / "tasks" / "QUERY_ISSUES_ROADMAP.md"

        # Ensure file doesn't exist
        assert not roadmap_file.exists()

        result = await task_generator_service._append_to_file("## QUERY-08: Test Task\n")

        assert result is True
        assert roadmap_file.exists()
        content = roadmap_file.read_text()
        assert "# PratikoAi Query System" in content
        assert "QUERY-08: Test Task" in content

    @pytest.mark.asyncio
    async def test_append_to_file_returns_false_on_permission_error(self, task_generator_service, tmp_path):
        """Test that file write failure returns False instead of raising."""
        task_generator_service.project_root = tmp_path

        # Mock the file open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "mkdir"):
                    result = await task_generator_service._append_to_file("## Test Task\n")

        assert result is False


class TestDatabaseFirstTaskIDGeneration:
    """Tests for database-first task ID generation.

    The service should query the database for max task_id first,
    then fall back to file scanning.
    """

    @pytest.mark.asyncio
    async def test_generate_task_id_from_database(self, task_generator_service):
        """Task ID is generated from database when DB has records."""
        # Mock database to return max task_id "QUERY-15"
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "QUERY-15"
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock file scan to return lower value
        with patch.object(task_generator_service, "_scan_file_for_max_task_number", return_value=10):
            task_id = await task_generator_service._generate_task_id(mock_session)

        # Should use DB value (15) not file value (10)
        assert task_id == "QUERY-16"

    @pytest.mark.asyncio
    async def test_generate_task_id_from_file_when_db_empty(self, task_generator_service):
        """Task ID uses file scan when database is empty."""
        # Mock database to return None
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock file scan to return higher value
        with patch.object(task_generator_service, "_scan_file_for_max_task_number", return_value=12):
            task_id = await task_generator_service._generate_task_id(mock_session)

        # Should use file value (12)
        assert task_id == "QUERY-13"

    @pytest.mark.asyncio
    async def test_generate_task_id_respects_minimum_with_db(self, task_generator_service):
        """Task ID starts from QUERY-08 even when DB/file have lower values."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "QUERY-03"  # Below minimum
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(task_generator_service, "_scan_file_for_max_task_number", return_value=5):
            task_id = await task_generator_service._generate_task_id(mock_session)

        # Should still be QUERY-08 (minimum)
        assert task_id == "QUERY-08"


class TestTaskGenerationWithDatabaseFirst:
    """Tests for end-to-end task generation with database-first approach."""

    @pytest.mark.asyncio
    async def test_generate_task_succeeds_when_file_missing(
        self, task_generator_service, sample_feedback, sample_expert, tmp_path
    ):
        """Task is created in database even if roadmap file doesn't exist."""
        sample_feedback.feedback_type = MagicMock()
        sample_feedback.feedback_type.value = "incomplete"

        task_generator_service.project_root = tmp_path
        # Don't create docs/tasks/ directory - file should be auto-created

        # Mock the database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=[sample_feedback, sample_expert])
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = Mock()

        # Mock the execute for task ID generation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing tasks
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.task_generator_service.AsyncSessionLocal", return_value=mock_session_ctx):
            task_id = await task_generator_service.generate_task_from_feedback(
                feedback_id=sample_feedback.id, expert_id=sample_expert.id
            )

        # Task should be created successfully even without pre-existing file
        assert task_id is not None
        assert task_id.startswith("QUERY-")
        # Verify task_creation_success was set to True
        assert sample_feedback.task_creation_success is True

    @pytest.mark.asyncio
    async def test_generate_task_writes_to_docs_tasks_folder(
        self, task_generator_service, sample_feedback, sample_expert, tmp_path
    ):
        """Task is written to docs/tasks/QUERY_ISSUES_ROADMAP.md."""
        sample_feedback.feedback_type = MagicMock()
        sample_feedback.feedback_type.value = "incorrect"

        task_generator_service.project_root = tmp_path
        docs_tasks = tmp_path / "docs" / "tasks"
        docs_tasks.mkdir(parents=True)
        roadmap = docs_tasks / "QUERY_ISSUES_ROADMAP.md"
        roadmap.write_text("# Tasks\n")

        # Mock the database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=[sample_feedback, sample_expert])
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = Mock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.task_generator_service.AsyncSessionLocal", return_value=mock_session_ctx):
            task_id = await task_generator_service.generate_task_from_feedback(
                feedback_id=sample_feedback.id, expert_id=sample_expert.id
            )

        # Verify file was written to docs/tasks/
        content = roadmap.read_text()
        assert task_id in content
        assert sample_feedback.query_text in content

    @pytest.mark.asyncio
    async def test_file_write_failure_does_not_prevent_task_creation(
        self, task_generator_service, sample_feedback, sample_expert, tmp_path
    ):
        """File write failure doesn't prevent task creation in database."""
        sample_feedback.feedback_type = MagicMock()
        sample_feedback.feedback_type.value = "incomplete"

        task_generator_service.project_root = tmp_path

        # Mock the database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=[sample_feedback, sample_expert])
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = Mock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.services.task_generator_service.AsyncSessionLocal", return_value=mock_session_ctx),
            patch.object(task_generator_service, "_append_to_file", return_value=False),
        ):
            task_id = await task_generator_service.generate_task_from_feedback(
                feedback_id=sample_feedback.id, expert_id=sample_expert.id
            )

        # Task should still be created successfully
        assert task_id is not None
        assert task_id.startswith("QUERY-")
        # Database save succeeded, so task_creation_success should be True
        assert sample_feedback.task_creation_success is True
