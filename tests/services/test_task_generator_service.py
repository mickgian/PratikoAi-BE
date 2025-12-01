"""Unit tests for TaskGeneratorService.

Tests the automatic task generation from expert feedback, including:
- Task ID generation (scanning files, incrementing max number)
- Task name generation (truncation, sanitization)
- Markdown formatting
- File operations (create, append)
- Database operations
- Error handling
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
def mock_db():
    """Mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = Mock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def task_generator_service(mock_db):
    """TaskGeneratorService instance with mock DB."""
    return TaskGeneratorService(db=mock_db)


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
    feedback.additional_details = "La risposta è incompleta perché non tratta i casi specifici."
    feedback.task_creation_attempted = False
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
    """Tests for task ID generation logic."""

    @pytest.mark.asyncio
    async def test_generate_task_id_no_existing_files(self, task_generator_service):
        """Test task ID generation when no files exist."""
        with patch.object(task_generator_service, "_scan_file_for_max_task_number", return_value=0):
            task_id = await task_generator_service._generate_task_id()

            assert task_id == "DEV-BE-1"

    @pytest.mark.asyncio
    async def test_generate_task_id_with_existing_tasks(self, task_generator_service):
        """Test task ID generation increments from max existing number."""

        # Mock roadmap has DEV-BE-45, tasks file has DEV-BE-50
        async def mock_scan(filepath, pattern):
            if "ARCHITECTURE_ROADMAP" in str(filepath):
                return 45
            elif "SUPER_USER_TASKS" in str(filepath):
                return 50
            return 0

        with patch.object(task_generator_service, "_scan_file_for_max_task_number", side_effect=mock_scan):
            task_id = await task_generator_service._generate_task_id()

            # Should be max(45, 50) + 1 = 51
            assert task_id == "DEV-BE-51"

    @pytest.mark.asyncio
    async def test_scan_file_for_max_task_number_file_exists(self, task_generator_service, tmp_path):
        """Test scanning file for task IDs when file exists."""
        # Create temp file with task IDs
        test_file = tmp_path / "test_tasks.md"
        test_file.write_text(
            """
        # Tasks
        - DEV-BE-10: Task 10
        - DEV-BE-25: Task 25
        - DEV-BE-15: Task 15
        """
        )

        max_num = await task_generator_service._scan_file_for_max_task_number(test_file, pattern=r"DEV-BE-(\d+)")

        assert max_num == 25

    @pytest.mark.asyncio
    async def test_scan_file_for_max_task_number_file_not_exists(self, task_generator_service, tmp_path):
        """Test scanning file returns 0 when file doesn't exist."""
        non_existent_file = tmp_path / "nonexistent.md"

        max_num = await task_generator_service._scan_file_for_max_task_number(
            non_existent_file, pattern=r"DEV-BE-(\d+)"
        )

        assert max_num == 0

    @pytest.mark.asyncio
    async def test_scan_file_for_max_task_number_no_matches(self, task_generator_service, tmp_path):
        """Test scanning file returns 0 when no task IDs found."""
        test_file = tmp_path / "test_empty.md"
        test_file.write_text("# No tasks here")

        max_num = await task_generator_service._scan_file_for_max_task_number(test_file, pattern=r"DEV-BE-(\d+)")

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
        task_id = "DEV-BE-123"
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
        assert "**Status:** 🔴 TODO" in markdown

    def test_create_task_markdown_includes_regulatory_references(
        self, task_generator_service, sample_feedback, sample_expert
    ):
        """Test markdown includes regulatory references when present."""
        sample_feedback.regulatory_references = ["Art. 1, L. 190/2014", "D.L. 119/2018"]

        markdown = task_generator_service._create_task_markdown("DEV-BE-123", "TASK", sample_feedback, sample_expert)

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

        markdown = task_generator_service._create_task_markdown("DEV-BE-123", "TASK", sample_feedback, sample_expert)

        assert "**Suggerimenti per il miglioramento:**" in markdown
        assert "Aggiungere casi specifici" in markdown
        assert "Citare normativa aggiornata" in markdown


class TestTaskGeneration:
    """Tests for end-to-end task generation."""

    @pytest.mark.asyncio
    async def test_generate_task_from_feedback_success(
        self, task_generator_service, sample_feedback, sample_expert, tmp_path
    ):
        """Test successful task generation from feedback."""
        # Mock file operations
        task_generator_service.project_root = tmp_path

        # Mock ID generation and database storage to avoid SQLAlchemy mapper issues
        with (
            patch.object(task_generator_service, "_generate_task_id", return_value="DEV-BE-100"),
            patch.object(task_generator_service, "_store_task_record", new_callable=AsyncMock),
        ):
            task_id = await task_generator_service.generate_task_from_feedback(sample_feedback, sample_expert)

            assert task_id == "DEV-BE-100"
            assert sample_feedback.generated_task_id == "DEV-BE-100"
            assert sample_feedback.task_creation_success is True

            # Verify file was created
            tasks_file = tmp_path / "SUPER_USER_TASKS.md"
            assert tasks_file.exists()

            content = tasks_file.read_text()
            assert "DEV-BE-100" in content
            assert sample_feedback.query_text in content

    @pytest.mark.asyncio
    async def test_generate_task_skips_correct_feedback(self, task_generator_service, sample_feedback, sample_expert):
        """Test task generation is skipped for 'correct' feedback."""
        sample_feedback.feedback_type = FeedbackType.CORRECT

        task_id = await task_generator_service.generate_task_from_feedback(sample_feedback, sample_expert)

        assert task_id is None

    @pytest.mark.asyncio
    async def test_generate_task_skips_without_additional_details(
        self, task_generator_service, sample_feedback, sample_expert
    ):
        """Test task generation is skipped without additional_details."""
        sample_feedback.additional_details = None

        task_id = await task_generator_service.generate_task_from_feedback(sample_feedback, sample_expert)

        assert task_id is None

    @pytest.mark.asyncio
    async def test_generate_task_handles_errors_gracefully(
        self, task_generator_service, sample_feedback, sample_expert
    ):
        """Test task generation handles errors without raising exceptions."""
        # Force an error by making _generate_task_id raise
        with patch.object(task_generator_service, "_generate_task_id", side_effect=Exception("Test error")):
            task_id = await task_generator_service.generate_task_from_feedback(sample_feedback, sample_expert)

            # Should return None and not raise
            assert task_id is None
            assert sample_feedback.task_creation_success is False
            assert "Test error" in sample_feedback.task_creation_error


class TestFileOperations:
    """Tests for file operations."""

    @pytest.mark.asyncio
    async def test_append_to_file_creates_file_if_not_exists(self, task_generator_service, tmp_path):
        """Test file is created with header if it doesn't exist."""
        task_generator_service.project_root = tmp_path
        tasks_file = tmp_path / "SUPER_USER_TASKS.md"

        assert not tasks_file.exists()

        await task_generator_service._append_to_file("## Test Task")

        assert tasks_file.exists()
        content = tasks_file.read_text()
        assert "# PratikoAi Backend - Tasks Generati dal Feedback Esperti" in content
        assert "## Test Task" in content

    @pytest.mark.asyncio
    async def test_append_to_file_appends_to_existing_file(self, task_generator_service, tmp_path):
        """Test content is appended to existing file."""
        task_generator_service.project_root = tmp_path
        tasks_file = tmp_path / "SUPER_USER_TASKS.md"

        # Create file with initial content
        tasks_file.write_text("# Existing Content\n")

        await task_generator_service._append_to_file("## New Task")

        content = tasks_file.read_text()
        assert "# Existing Content" in content
        assert "## New Task" in content
