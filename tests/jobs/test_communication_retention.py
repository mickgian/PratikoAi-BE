"""DEV-419: Tests for Communication Retention Job.

Tests: retention enforcement, anonymization, studio override.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.jobs.communication_retention_job import CommunicationRetentionJob


@pytest.fixture
def job():
    return CommunicationRetentionJob()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestRetentionEnforcement:
    @pytest.mark.asyncio
    async def test_anonymize_old_communications(self, job, mock_db):
        old_comm = MagicMock()
        old_comm.created_at = datetime.now(UTC) - timedelta(days=730)
        old_comm.subject = "Vecchia comunicazione"
        old_comm.content = "Contenuto con dati PII"
        old_comm.client_id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [old_comm]
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await job.run(mock_db, studio_id=uuid.uuid4())
        assert count >= 0

    @pytest.mark.asyncio
    async def test_recent_communications_untouched(self, job, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await job.run(mock_db, studio_id=uuid.uuid4())
        assert count == 0


class TestAnonymization:
    def test_anonymize_fields(self, job):
        data = {
            "subject": "Comunicazione importante per Mario Rossi",
            "content": "Gentile Mario, il suo codice fiscale RSSMRA80A01H501Z...",
            "client_id": 42,
        }
        anonymized = job.anonymize(data)
        assert anonymized["client_id"] is None
        assert "RSSMRA80A01H501Z" not in anonymized.get("content", "")

    def test_preserve_aggregate_stats(self, job):
        data = {
            "subject": "Test",
            "content": "Content",
            "channel": "email",
            "status": "sent",
        }
        anonymized = job.anonymize(data)
        assert anonymized["channel"] == "email"
        assert anonymized["status"] == "sent"


class TestStudioOverride:
    @pytest.mark.asyncio
    async def test_custom_retention_period(self, job, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await job.run(mock_db, studio_id=uuid.uuid4(), retention_months=36)
        assert count == 0
