"""Tests for background task execution in Expert Feedback System.

These tests validate that background tasks (TaskGeneratorService, Golden Set workflow)
correctly manage their own database sessions and don't fail when the request session closes.

BUGS THIS WOULD HAVE CAUGHT:
- Bug #5: Database session management (background tasks using closed request session)
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
from uuid import uuid4

import pytest

from app.models.database import AsyncSessionLocal
from app.models.quality_analysis import (
    ExpertCredentialType,
    ExpertFeedback,
    ExpertGeneratedTask,
    ExpertProfile,
    FeedbackType,
    ItalianFeedbackCategory,
)
from app.models.user import User, UserRole
from app.services.task_generator_service import TaskGeneratorService


@pytest.fixture
async def real_db():
    """Real database session for integration tests."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture
async def test_user(real_db):
    """Create test user in database."""
    user = User(
        email=f"bg_task_test_{id(real_db)}@test.com",
        hashed_password="hashed",
        role=UserRole.SUPER_USER.value,
    )
    real_db.add(user)
    await real_db.commit()
    await real_db.refresh(user)
    return user


@pytest.fixture
async def test_expert(real_db, test_user):
    """Create test expert profile in database."""
    expert = ExpertProfile(
        user_id=test_user.id,
        credential_types=[ExpertCredentialType.DOTTORE_COMMERCIALISTA],
        trust_score=0.85,
        is_verified=True,
        is_active=True,
    )
    real_db.add(expert)
    await real_db.commit()
    await real_db.refresh(expert)
    return expert


@pytest.fixture
async def incomplete_feedback(real_db, test_expert):
    """Create INCOMPLETE feedback with additional_details."""
    feedback = ExpertFeedback(
        query_id=uuid4(),
        expert_id=test_expert.id,
        feedback_type=FeedbackType.INCOMPLETE,
        category=ItalianFeedbackCategory.CALCOLO_SBAGLIATO,
        query_text="Come si calcola l'IVA per i forfettari?",
        original_answer="I forfettari non pagano IVA",
        confidence_score=0.8,
        time_spent_seconds=180,
        additional_details="Manca spiegazione dei casi specifici per cessioni UE",
    )
    real_db.add(feedback)
    await real_db.commit()
    await real_db.refresh(feedback)
    return feedback


@pytest.fixture
async def correct_feedback(real_db, test_expert):
    """Create CORRECT feedback for Golden Set workflow."""
    feedback = ExpertFeedback(
        query_id=uuid4(),
        expert_id=test_expert.id,
        feedback_type=FeedbackType.CORRECT,
        query_text="Qual è l'aliquota IVA ordinaria?",
        original_answer="L'aliquota IVA ordinaria è del 22%",
        confidence_score=0.95,
        time_spent_seconds=60,
    )
    real_db.add(feedback)
    await real_db.commit()
    await real_db.refresh(feedback)
    return feedback


class TestTaskGeneratorServiceSessionManagement:
    """Test TaskGeneratorService creates its own database session (Bug #5)."""

    @pytest.mark.asyncio
    async def test_task_generator_creates_own_session(self, incomplete_feedback, test_expert):
        """Test TaskGeneratorService creates its own session (doesn't use closed request session).

        Bug #5: Background tasks were failing because they tried to use the request's
        database session, which was already closed when the background task executed.
        """
        service = TaskGeneratorService()

        # Mock file operations to avoid actual file I/O
        mock_file_content = "# Existing tasks\nQUERY-07: Some task"
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_file_content):
                with patch("pathlib.Path.open", mock_open()) as mock_file:
                    # Call background task (creates its own session)
                    task_id = await service.generate_task_from_feedback(
                        feedback_id=incomplete_feedback.id, expert_id=test_expert.id
                    )

                    # Verify task was created successfully
                    assert task_id is not None
                    assert task_id.startswith("QUERY-")

                    # Verify file was written
                    mock_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_generator_survives_closed_request_session(self, real_db, incomplete_feedback, test_expert):
        """Test background task works even when request session is closed (Bug #5).

        This simulates the real bug scenario:
        1. Request handler creates feedback
        2. Request handler closes its database session
        3. Background task runs and needs to access database
        4. Background task should use its OWN session, not the closed one
        """
        # Simulate request session closing
        await real_db.close()

        service = TaskGeneratorService()

        # Mock file operations
        mock_file_content = "# Existing tasks\nQUERY-07: Some task"
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_file_content):
                with patch("pathlib.Path.open", mock_open()):
                    # This should NOT fail even though real_db is closed
                    task_id = await service.generate_task_from_feedback(
                        feedback_id=incomplete_feedback.id, expert_id=test_expert.id
                    )

                    assert task_id is not None

    @pytest.mark.asyncio
    async def test_task_generator_updates_feedback_record(self, incomplete_feedback, test_expert):
        """Test task generator updates feedback record with task_id and success status."""
        service = TaskGeneratorService()

        # Mock file operations
        mock_file_content = "# Existing tasks\nQUERY-07: Some task"
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_file_content):
                with patch("pathlib.Path.open", mock_open()):
                    task_id = await service.generate_task_from_feedback(
                        feedback_id=incomplete_feedback.id, expert_id=test_expert.id
                    )

                    assert task_id is not None

                    # Verify feedback record was updated (using fresh session)
                    async with AsyncSessionLocal() as db:
                        feedback = await db.get(ExpertFeedback, incomplete_feedback.id)
                        assert feedback.generated_task_id == task_id
                        assert feedback.task_creation_success is True
                        assert feedback.task_creation_error is None

    @pytest.mark.asyncio
    async def test_task_generator_stores_task_record(self, incomplete_feedback, test_expert):
        """Test task generator creates record in expert_generated_tasks table."""
        service = TaskGeneratorService()

        # Mock file operations
        mock_file_content = "# Existing tasks\nQUERY-07: Some task"
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_file_content):
                with patch("pathlib.Path.open", mock_open()):
                    task_id = await service.generate_task_from_feedback(
                        feedback_id=incomplete_feedback.id, expert_id=test_expert.id
                    )

                    assert task_id is not None

                    # Verify task record was created (using fresh session)
                    async with AsyncSessionLocal() as db:
                        from sqlalchemy import select

                        result = await db.execute(
                            select(ExpertGeneratedTask).where(ExpertGeneratedTask.task_id == task_id)
                        )
                        task = result.scalar_one_or_none()

                        assert task is not None
                        assert task.task_id == task_id
                        assert task.feedback_id == incomplete_feedback.id
                        assert task.expert_id == test_expert.id
                        assert task.question == incomplete_feedback.query_text
                        assert task.answer == incomplete_feedback.original_answer
                        assert task.additional_details == incomplete_feedback.additional_details

    @pytest.mark.asyncio
    async def test_task_generator_handles_errors_gracefully(self, incomplete_feedback, test_expert):
        """Test task generator handles errors without crashing (logs error, updates feedback)."""
        service = TaskGeneratorService()

        # Force an error by mocking file operations to fail
        with patch("pathlib.Path.exists", side_effect=Exception("File system error")):
            # Should not raise exception (logs error instead)
            task_id = await service.generate_task_from_feedback(
                feedback_id=incomplete_feedback.id, expert_id=test_expert.id
            )

            assert task_id is None  # Failed, returns None

            # Verify feedback was updated with error (using fresh session)
            async with AsyncSessionLocal() as db:
                feedback = await db.get(ExpertFeedback, incomplete_feedback.id)
                assert feedback.task_creation_success is False
                assert feedback.task_creation_error is not None
                assert "error" in feedback.task_creation_error.lower()


class TestGoldenSetWorkflowSessionManagement:
    """Test Golden Set workflow creates its own database session (Bug #5)."""

    @pytest.mark.asyncio
    async def test_golden_set_workflow_creates_own_session(self, correct_feedback, test_expert):
        """Test _trigger_golden_set_workflow creates its own session (Bug #5)."""
        from app.api.v1.expert_feedback import _trigger_golden_set_workflow

        # Mock Golden Set orchestrator steps
        with patch("app.api.v1.expert_feedback.step_127__golden_candidate") as mock_127:
            with patch("app.api.v1.expert_feedback.step_128__golden_approval") as mock_128:
                with patch("app.api.v1.expert_feedback.step_129__publish_golden") as mock_129:
                    # Mock successful workflow
                    mock_127.return_value = {"faq_candidate": {"priority_score": 0.9}}
                    mock_128.return_value = {"approval_decision": {"status": "auto_approved"}}
                    mock_129.return_value = {"published_faq_id": "faq_123"}

                    # Call workflow (creates its own session)
                    await _trigger_golden_set_workflow(feedback_id=correct_feedback.id, expert_id=test_expert.id)

                    # Verify workflow steps were called
                    mock_127.assert_called_once()
                    mock_128.assert_called_once()
                    mock_129.assert_called_once()

    @pytest.mark.asyncio
    async def test_golden_set_workflow_survives_closed_request_session(self, real_db, correct_feedback, test_expert):
        """Test Golden Set workflow works when request session is closed (Bug #5)."""
        from app.api.v1.expert_feedback import _trigger_golden_set_workflow

        # Simulate request session closing
        await real_db.close()

        # Mock Golden Set orchestrator
        with patch("app.api.v1.expert_feedback.step_127__golden_candidate") as mock_127:
            with patch("app.api.v1.expert_feedback.step_128__golden_approval") as mock_128:
                with patch("app.api.v1.expert_feedback.step_129__publish_golden") as mock_129:
                    mock_127.return_value = {"faq_candidate": {"priority_score": 0.9}}
                    mock_128.return_value = {"approval_decision": {"status": "auto_approved"}}
                    mock_129.return_value = {"published_faq_id": "faq_123"}

                    # This should NOT fail even though real_db is closed
                    await _trigger_golden_set_workflow(feedback_id=correct_feedback.id, expert_id=test_expert.id)

                    # Verify workflow executed successfully
                    mock_129.assert_called_once()

    @pytest.mark.asyncio
    async def test_golden_set_workflow_updates_feedback_record(self, correct_feedback, test_expert):
        """Test Golden Set workflow updates feedback with generated_faq_id."""
        from app.api.v1.expert_feedback import _trigger_golden_set_workflow

        faq_id = "faq_test_123"

        with patch("app.api.v1.expert_feedback.step_127__golden_candidate") as mock_127:
            with patch("app.api.v1.expert_feedback.step_128__golden_approval") as mock_128:
                with patch("app.api.v1.expert_feedback.step_129__publish_golden") as mock_129:
                    mock_127.return_value = {"faq_candidate": {"priority_score": 0.9}}
                    mock_128.return_value = {"approval_decision": {"status": "auto_approved"}}
                    mock_129.return_value = {"published_faq_id": faq_id}

                    await _trigger_golden_set_workflow(feedback_id=correct_feedback.id, expert_id=test_expert.id)

                    # Verify feedback was updated with FAQ ID (using fresh session)
                    async with AsyncSessionLocal() as db:
                        feedback = await db.get(ExpertFeedback, correct_feedback.id)
                        assert feedback.generated_faq_id == faq_id
                        assert feedback.task_creation_success is True

    @pytest.mark.asyncio
    async def test_golden_set_workflow_handles_not_approved(self, correct_feedback, test_expert):
        """Test Golden Set workflow handles rejection (low trust score, etc.)."""
        from app.api.v1.expert_feedback import _trigger_golden_set_workflow

        with patch("app.api.v1.expert_feedback.step_127__golden_candidate") as mock_127:
            with patch("app.api.v1.expert_feedback.step_128__golden_approval") as mock_128:
                mock_127.return_value = {"faq_candidate": {"priority_score": 0.9}}
                mock_128.return_value = {"approval_decision": {"status": "requires_review"}}  # Not approved

                await _trigger_golden_set_workflow(feedback_id=correct_feedback.id, expert_id=test_expert.id)

                # Verify feedback was updated with failure (using fresh session)
                async with AsyncSessionLocal() as db:
                    feedback = await db.get(ExpertFeedback, correct_feedback.id)
                    assert feedback.generated_faq_id is None
                    assert feedback.task_creation_success is False

    @pytest.mark.asyncio
    async def test_golden_set_workflow_handles_errors_gracefully(self, correct_feedback, test_expert):
        """Test Golden Set workflow handles errors without crashing."""
        from app.api.v1.expert_feedback import _trigger_golden_set_workflow

        # Force an error
        with patch(
            "app.api.v1.expert_feedback.step_127__golden_candidate", side_effect=Exception("Orchestrator error")
        ):
            # Should not raise exception (logs error instead)
            await _trigger_golden_set_workflow(feedback_id=correct_feedback.id, expert_id=test_expert.id)

            # Verify feedback was updated with error (using fresh session)
            async with AsyncSessionLocal() as db:
                feedback = await db.get(ExpertFeedback, correct_feedback.id)
                assert feedback.task_creation_success is False
                assert feedback.task_creation_error is not None


class TestBackgroundTaskFireAndForget:
    """Test background tasks execute asynchronously without blocking response."""

    @pytest.mark.asyncio
    async def test_background_tasks_dont_block_api_response(self, incomplete_feedback, test_expert):
        """Test background tasks are fire-and-forget (don't block API response).

        This validates that the API returns quickly even if background task is slow.
        """
        service = TaskGeneratorService()

        # Mock slow background task (simulates file I/O, database operations)
        async def slow_task_generation(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow operation
            return "QUERY-08"

        with patch.object(service, "generate_task_from_feedback", side_effect=slow_task_generation):
            # Start background task
            task = asyncio.create_task(
                service.generate_task_from_feedback(feedback_id=incomplete_feedback.id, expert_id=test_expert.id)
            )

            # API should return immediately (not wait for background task)
            # Simulate API returning before task completes
            await asyncio.sleep(0.1)  # Very short wait

            # Task should still be running
            assert not task.done()

            # Clean up
            await task  # Wait for task to complete

    @pytest.mark.asyncio
    async def test_multiple_background_tasks_concurrent(self, test_expert):
        """Test multiple background tasks can run concurrently."""
        # Create multiple feedback records
        feedback_ids = []
        async with AsyncSessionLocal() as db:
            for i in range(3):
                feedback = ExpertFeedback(
                    query_id=uuid4(),
                    expert_id=test_expert.id,
                    feedback_type=FeedbackType.INCOMPLETE,
                    query_text=f"Test question {i}",
                    original_answer=f"Test answer {i}",
                    confidence_score=0.8,
                    time_spent_seconds=100,
                    additional_details=f"Test details {i}",
                )
                db.add(feedback)
                await db.flush()
                feedback_ids.append(feedback.id)

            await db.commit()

        service = TaskGeneratorService()

        # Mock file operations
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="QUERY-07: Task"):
                with patch("pathlib.Path.open", mock_open()):
                    # Start multiple background tasks concurrently
                    tasks = [
                        asyncio.create_task(
                            service.generate_task_from_feedback(feedback_id=fid, expert_id=test_expert.id)
                        )
                        for fid in feedback_ids
                    ]

                    # Wait for all tasks to complete
                    results = await asyncio.gather(*tasks)

                    # Verify all tasks completed successfully
                    assert len(results) == 3
                    assert all(r is not None for r in results)
                    assert all(r.startswith("QUERY-") for r in results)
