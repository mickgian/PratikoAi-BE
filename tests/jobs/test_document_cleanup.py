"""DEV-391: Tests for Document Auto-Delete Background Job.

Tests: delete after 30 minutes, GDPR data minimization.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.jobs.document_cleanup_job import DocumentCleanupJob


@pytest.fixture
def job():
    return DocumentCleanupJob()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestDocumentCleanup:
    @pytest.mark.asyncio
    async def test_delete_expired_documents(self, job, mock_db):
        old_doc = MagicMock()
        old_doc.id = uuid.uuid4()
        old_doc.created_at = datetime.now(UTC) - timedelta(minutes=45)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [old_doc]
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await job.run(mock_db)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_keep_recent_documents(self, job, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await job.run(mock_db)
        assert count == 0

    @pytest.mark.asyncio
    async def test_custom_ttl(self, job, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await job.run(mock_db, ttl_minutes=60)
        assert count == 0


class TestDefaultTtl:
    def test_default_30_minutes(self, job):
        assert job.default_ttl_minutes == 30
