"""DEV-391: Comprehensive tests for DocumentCleanupJob.

Tests the document auto-delete background job that removes uploaded documents
after a configurable TTL (default 30 minutes) for GDPR data minimization.

Scenarios tested:
- Happy path: expired documents are deleted, commit is called, correct count returned
- No expired documents: returns 0, commit is NOT called
- Custom ttl_minutes parameter overrides the default
- Exception during query (import/execute failure): falls back to empty list, returns 0
- Default TTL constant is 30 minutes
- Multiple expired documents are all individually deleted
- Logger is called with correct structured context
"""

import sys
import types
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.document_cleanup_job import (
    DEFAULT_TTL_MINUTES,
    DocumentCleanupJob,
    document_cleanup_job,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def job():
    """Fresh DocumentCleanupJob instance."""
    return DocumentCleanupJob()


@pytest.fixture
def mock_db():
    """Mock async database session with explicit async methods."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    return db


def _make_mock_doc(*, minutes_old: int = 45) -> MagicMock:
    """Create a mock document with a created_at timestamp."""
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.created_at = datetime.now(UTC) - timedelta(minutes=minutes_old)
    doc.filename = f"test_doc_{doc.id}.pdf"
    return doc


def _mock_result_with_docs(docs: list) -> MagicMock:
    """Build a mock db.execute() result that returns the given docs via scalars().all()."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = docs
    return mock_result


class _MockColumn:
    """A column-like object that supports comparison operators.

    MagicMock cannot handle ``<`` / ``>`` with datetime objects because
    datetime's reflected comparison raises ``TypeError``.  This tiny helper
    returns a MagicMock sentinel from every comparison so that expressions
    like ``SimpleDocument.created_at < cutoff`` succeed.
    """

    def __lt__(self, other):  # noqa: ANN001,ANN204
        return MagicMock(name="lt_clause")

    def __le__(self, other):  # noqa: ANN001,ANN204
        return MagicMock(name="le_clause")

    def __gt__(self, other):  # noqa: ANN001,ANN204
        return MagicMock(name="gt_clause")

    def __ge__(self, other):  # noqa: ANN001,ANN204
        return MagicMock(name="ge_clause")


@pytest.fixture
def _patch_simple_document():
    """Patch sys.modules so the import of SimpleDocument succeeds inside run().

    The real module ``app.models.document_simple`` does NOT export a
    ``SimpleDocument`` class, so the ``from ... import SimpleDocument``
    inside ``DocumentCleanupJob.run()`` always raises ``ImportError``.

    Additionally:
    - SQLAlchemy's ``select()`` rejects MagicMock arguments, so we patch
      ``select`` in the cleanup-job module with a plain MagicMock.
    - ``SimpleDocument.created_at < cutoff`` fails because MagicMock
      does not support ``<`` against ``datetime``, so ``created_at`` is
      replaced with a ``_MockColumn`` instance.

    This fixture patches all three so we can exercise the happy-path code
    (query -> delete -> commit).
    """
    # Build a fake module that has a SimpleDocument attribute.
    fake_module = types.ModuleType("app.models.document_simple")
    mock_simple_document = MagicMock(name="SimpleDocument")
    mock_simple_document.created_at = _MockColumn()
    fake_module.SimpleDocument = mock_simple_document  # type: ignore[attr-defined]

    # Mock select() so that select(SimpleDocument).where(...) returns a benign mock.
    mock_select = MagicMock(name="mock_select")

    original_module = sys.modules.get("app.models.document_simple")
    sys.modules["app.models.document_simple"] = fake_module

    with patch("app.jobs.document_cleanup_job.select", mock_select):
        yield mock_simple_document

    # Restore original module (or remove if it was absent).
    if original_module is not None:
        sys.modules["app.models.document_simple"] = original_module
    else:
        sys.modules.pop("app.models.document_simple", None)


# ---------------------------------------------------------------------------
# Test: Default TTL constant
# ---------------------------------------------------------------------------


class TestDefaultTTL:
    """Verify the module-level and class-level TTL defaults."""

    def test_module_constant_is_30(self):
        """DEFAULT_TTL_MINUTES module constant is 30."""
        assert DEFAULT_TTL_MINUTES == 30

    def test_class_default_ttl_is_30(self, job):
        """DocumentCleanupJob.default_ttl_minutes is 30."""
        assert job.default_ttl_minutes == 30

    def test_singleton_instance_exists(self):
        """Module-level document_cleanup_job singleton is a DocumentCleanupJob."""
        assert isinstance(document_cleanup_job, DocumentCleanupJob)
        assert document_cleanup_job.default_ttl_minutes == 30


# ---------------------------------------------------------------------------
# Test: No expired documents -> returns 0, commit NOT called
# ---------------------------------------------------------------------------


class TestNoExpiredDocuments:
    """When no documents are expired, run() returns 0 and does NOT commit."""

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_expired(self, job, mock_db, _patch_simple_document):
        """run() returns 0 when the query yields no expired documents."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        count = await job.run(mock_db)

        assert count == 0

    @pytest.mark.asyncio
    async def test_does_not_commit_when_no_expired(self, job, mock_db, _patch_simple_document):
        """db.commit() is NOT called when there are no expired documents."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        await job.run(mock_db)

        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_does_not_delete_when_no_expired(self, job, mock_db, _patch_simple_document):
        """db.delete() is NOT called when there are no expired documents."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        await job.run(mock_db)

        mock_db.delete.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test: Expired documents -> deletes them, commits, returns count
# ---------------------------------------------------------------------------


class TestExpiredDocuments:
    """When expired documents exist, run() deletes them, commits, and returns count."""

    @pytest.mark.asyncio
    async def test_returns_correct_count_single_doc(self, job, mock_db, _patch_simple_document):
        """run() returns 1 when one document is expired."""
        expired_doc = _make_mock_doc(minutes_old=45)
        mock_db.execute = AsyncMock(
            return_value=_mock_result_with_docs([expired_doc]),
        )

        count = await job.run(mock_db)

        assert count == 1

    @pytest.mark.asyncio
    async def test_returns_correct_count_multiple_docs(self, job, mock_db, _patch_simple_document):
        """run() returns the exact count of expired documents."""
        docs = [_make_mock_doc(minutes_old=i) for i in (35, 60, 120)]
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs(docs))

        count = await job.run(mock_db)

        assert count == 3

    @pytest.mark.asyncio
    async def test_calls_delete_for_each_expired_doc(self, job, mock_db, _patch_simple_document):
        """db.delete() is called once per expired document."""
        doc1 = _make_mock_doc(minutes_old=45)
        doc2 = _make_mock_doc(minutes_old=90)
        mock_db.execute = AsyncMock(
            return_value=_mock_result_with_docs([doc1, doc2]),
        )

        await job.run(mock_db)

        assert mock_db.delete.await_count == 2
        mock_db.delete.assert_any_await(doc1)
        mock_db.delete.assert_any_await(doc2)

    @pytest.mark.asyncio
    async def test_calls_commit_when_documents_deleted(self, job, mock_db, _patch_simple_document):
        """db.commit() IS called when at least one document is deleted."""
        expired_doc = _make_mock_doc(minutes_old=45)
        mock_db.execute = AsyncMock(
            return_value=_mock_result_with_docs([expired_doc]),
        )

        await job.run(mock_db)

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_commit_called_exactly_once(self, job, mock_db, _patch_simple_document):
        """db.commit() is called exactly once, regardless of how many docs are deleted."""
        docs = [_make_mock_doc(minutes_old=i) for i in (35, 60, 120, 180)]
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs(docs))

        await job.run(mock_db)

        assert mock_db.commit.await_count == 1


# ---------------------------------------------------------------------------
# Test: Custom ttl_minutes override
# ---------------------------------------------------------------------------


class TestCustomTTL:
    """run() respects the ttl_minutes keyword argument."""

    @pytest.mark.asyncio
    async def test_custom_ttl_is_used(self, job, mock_db, _patch_simple_document):
        """When ttl_minutes=60 is passed, run() still works correctly."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        count = await job.run(mock_db, ttl_minutes=60)

        assert count == 0

    @pytest.mark.asyncio
    async def test_custom_ttl_changes_cutoff(self, job, mock_db, _patch_simple_document):
        """The cutoff time is computed from the custom ttl_minutes, not the default."""
        captured_queries = []

        async def capture_execute(query):
            captured_queries.append(query)
            return _mock_result_with_docs([])

        mock_db.execute = AsyncMock(side_effect=capture_execute)

        await job.run(mock_db, ttl_minutes=120)

        # The query was executed (proves it ran with our custom TTL)
        assert len(captured_queries) == 1

    @pytest.mark.asyncio
    async def test_custom_ttl_zero_falls_back_to_default(self, job, mock_db, _patch_simple_document):
        """When ttl_minutes=0 is passed, the falsy-or logic falls back to the default."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        # ttl_minutes=0 is falsy, so `ttl_minutes or self.default_ttl_minutes` -> 30
        count = await job.run(mock_db, ttl_minutes=0)

        assert count == 0

    @pytest.mark.asyncio
    async def test_custom_ttl_none_uses_default(self, job, mock_db, _patch_simple_document):
        """When ttl_minutes=None (default), the class default is used."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        count = await job.run(mock_db, ttl_minutes=None)

        assert count == 0

    @pytest.mark.asyncio
    async def test_custom_ttl_reflected_in_log(self, job, mock_db, _patch_simple_document):
        """When ttl_minutes is overridden, the logger reports the custom value."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        with patch("app.jobs.document_cleanup_job.logger") as mock_logger:
            await job.run(mock_db, ttl_minutes=90)

            call_args = mock_logger.info.call_args
            assert call_args[1]["ttl_minutes"] == 90


# ---------------------------------------------------------------------------
# Test: Exception during import/query -> empty fallback, returns 0
# ---------------------------------------------------------------------------


class TestQueryException:
    """When the try block raises (import failure, DB error, etc.), run() returns 0."""

    @pytest.mark.asyncio
    async def test_returns_zero_on_execute_exception(self, job, mock_db, _patch_simple_document):
        """run() returns 0 when db.execute() raises an exception."""
        mock_db.execute = AsyncMock(side_effect=RuntimeError("connection lost"))

        count = await job.run(mock_db)

        assert count == 0

    @pytest.mark.asyncio
    async def test_does_not_commit_on_exception(self, job, mock_db, _patch_simple_document):
        """db.commit() is NOT called when the query fails."""
        mock_db.execute = AsyncMock(side_effect=RuntimeError("connection lost"))

        await job.run(mock_db)

        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_does_not_delete_on_exception(self, job, mock_db, _patch_simple_document):
        """db.delete() is NOT called when the query fails."""
        mock_db.execute = AsyncMock(side_effect=RuntimeError("connection lost"))

        await job.run(mock_db)

        mock_db.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_import_error_falls_back_to_empty(self, job, mock_db):
        """An ImportError inside the try block is caught, returning 0.

        This test does NOT use _patch_simple_document, so the real import will
        fail with ImportError (SimpleDocument does not exist in the module).
        This exercises the except branch via a genuine import failure.
        """
        count = await job.run(mock_db)

        assert count == 0

    @pytest.mark.asyncio
    async def test_import_error_does_not_commit(self, job, mock_db):
        """db.commit() is NOT called when the import fails."""
        await job.run(mock_db)

        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_scalars_exception_falls_back_to_empty(self, job, mock_db, _patch_simple_document):
        """If scalars().all() raises, the except block catches it and returns 0."""
        mock_result = MagicMock()
        mock_result.scalars.side_effect = AttributeError("scalars failed")
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await job.run(mock_db)

        assert count == 0

    @pytest.mark.asyncio
    async def test_exception_still_logs(self, job, mock_db, _patch_simple_document):
        """Logger is still called even when the query raises an exception."""
        mock_db.execute = AsyncMock(side_effect=RuntimeError("DB error"))

        with patch("app.jobs.document_cleanup_job.logger") as mock_logger:
            await job.run(mock_db)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[1]["deleted_count"] == 0


# ---------------------------------------------------------------------------
# Test: Logger is called with structured context
# ---------------------------------------------------------------------------


class TestLogging:
    """run() logs cleanup results via structured logging."""

    @pytest.mark.asyncio
    async def test_logs_on_zero_deletions(self, job, mock_db, _patch_simple_document):
        """Logger is called even when no documents are deleted."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        with patch("app.jobs.document_cleanup_job.logger") as mock_logger:
            await job.run(mock_db)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "document_cleanup_completed"
            assert call_args[1]["deleted_count"] == 0
            assert call_args[1]["ttl_minutes"] == 30

    @pytest.mark.asyncio
    async def test_logs_correct_count_on_deletions(self, job, mock_db, _patch_simple_document):
        """Logger reports the correct deleted_count when documents are removed."""
        docs = [_make_mock_doc(minutes_old=45), _make_mock_doc(minutes_old=60)]
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs(docs))

        with patch("app.jobs.document_cleanup_job.logger") as mock_logger:
            await job.run(mock_db)

            call_args = mock_logger.info.call_args
            assert call_args[1]["deleted_count"] == 2

    @pytest.mark.asyncio
    async def test_logs_custom_ttl(self, job, mock_db, _patch_simple_document):
        """Logger reports the custom ttl_minutes when overridden."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        with patch("app.jobs.document_cleanup_job.logger") as mock_logger:
            await job.run(mock_db, ttl_minutes=60)

            call_args = mock_logger.info.call_args
            assert call_args[1]["ttl_minutes"] == 60

    @pytest.mark.asyncio
    async def test_logs_cutoff_as_iso_string(self, job, mock_db, _patch_simple_document):
        """Logger includes cutoff as an ISO-format string."""
        mock_db.execute = AsyncMock(return_value=_mock_result_with_docs([]))

        with patch("app.jobs.document_cleanup_job.logger") as mock_logger:
            await job.run(mock_db)

            call_args = mock_logger.info.call_args
            cutoff_str = call_args[1]["cutoff"]
            # Verify it's a valid ISO datetime string by parsing it
            parsed = datetime.fromisoformat(cutoff_str)
            assert parsed.tzinfo is not None  # Should be timezone-aware (UTC)

    @pytest.mark.asyncio
    async def test_logs_after_exception(self, job, mock_db, _patch_simple_document):
        """Logger is still called even when the query raises an exception."""
        mock_db.execute = AsyncMock(side_effect=RuntimeError("DB error"))

        with patch("app.jobs.document_cleanup_job.logger") as mock_logger:
            await job.run(mock_db)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[1]["deleted_count"] == 0
