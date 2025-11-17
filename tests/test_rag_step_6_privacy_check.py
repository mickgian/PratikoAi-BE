#!/usr/bin/env python3
"""
Tests for RAG STEP 6 — PRIVACY_ANONYMIZE_REQUESTS enabled?

This step checks if privacy anonymization is enabled in settings.
It's a decision node that routes to either anonymization or direct workflow initialization.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep6PrivacyCheck:
    """Test suite for RAG STEP 6 - Privacy anonymize requests enabled"""

    @pytest.fixture
    def mock_session(self):
        """Mock session object."""
        session = MagicMock()
        session.id = "session_123"
        session.user_id = 456
        return session

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = MagicMock()
        user.id = 456
        user.email = "user@example.com"
        return user

    @pytest.fixture
    def mock_validated_request(self):
        """Mock validated request."""
        return {"messages": [{"role": "user", "content": "What are my tax obligations?"}], "user_id": 456}

    @pytest.fixture
    def mock_gdpr_record(self):
        """Mock GDPR record from Step 4."""
        return {"processing_id": "proc_123", "recorded_at": "2024-01-01T10:00:00Z", "status": "recorded"}

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.settings")
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.orchestrators.privacy.logger")
    async def test_step_6_privacy_enabled(
        self,
        mock_logger,
        mock_rag_log,
        mock_settings,
        mock_session,
        mock_user,
        mock_validated_request,
        mock_gdpr_record,
    ):
        """Test Step 6: Privacy anonymization enabled"""
        from app.orchestrators.privacy import step_6__privacy_check

        # Enable privacy anonymization
        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = True

        # Context from Step 4 (GDPRLog)
        ctx = {
            "gdpr_record": mock_gdpr_record,
            "validated_request": mock_validated_request,
            "session": mock_session,
            "user": mock_user,
            "request_metadata": {"request_id": "req_123"},
        }

        # Call the orchestrator function
        result = await step_6__privacy_check(ctx=ctx)

        # Verify result structure
        assert isinstance(result, dict)
        assert result["privacy_enabled"] is True
        assert result["anonymization_required"] is True
        assert result["next_step"] == "AnonymizeText"
        assert result["decision"] == "anonymize_enabled"
        assert "privacy_settings" in result

        # Verify data is preserved for next step
        assert result["validated_request"] == mock_validated_request
        assert result["session"] == mock_session
        assert result["user"] == mock_user

        # Verify logging
        mock_logger.info.assert_called()
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Privacy anonymization enabled" in call for call in log_calls)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]
        assert len(completed_logs) > 0
        log_call = completed_logs[0]
        assert log_call[1]["step"] == 6
        assert log_call[1]["privacy_enabled"] is True
        assert log_call[1]["decision"] == "anonymize_enabled"

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.config.settings")
    async def test_step_6_privacy_disabled(
        self,
        mock_settings,
        mock_logger,
        mock_rag_log,
        mock_session,
        mock_user,
        mock_validated_request,
        mock_gdpr_record,
    ):
        """Test Step 6: Privacy anonymization disabled"""
        from app.orchestrators.privacy import step_6__privacy_check

        # Disable privacy anonymization
        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = False

        ctx = {
            "gdpr_record": mock_gdpr_record,
            "validated_request": mock_validated_request,
            "session": mock_session,
            "user": mock_user,
        }

        result = await step_6__privacy_check(ctx=ctx)

        # Should route directly to workflow initialization
        assert result["privacy_enabled"] is False
        assert result["anonymization_required"] is False
        assert result["next_step"] == "InitAgent"
        assert result["decision"] == "anonymize_disabled"

        # Verify logging
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Privacy anonymization disabled" in call for call in log_calls)

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.config.settings")
    async def test_step_6_missing_context(self, mock_settings, mock_logger, mock_rag_log):
        """Test Step 6: Handle missing context gracefully"""
        from app.orchestrators.privacy import step_6__privacy_check

        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = True

        # Call with minimal context
        result = await step_6__privacy_check()

        # Should still make decision but log warning
        assert result["privacy_enabled"] is True
        assert result["anonymization_required"] is True
        assert result["next_step"] == "AnonymizeText"
        assert "Missing context data" in result["warning"]

        # Verify warning logged
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.config.settings")
    async def test_step_6_environment_specific_settings(
        self, mock_settings, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request
    ):
        """Test Step 6: Environment-specific privacy settings"""
        from app.orchestrators.privacy import step_6__privacy_check

        # Test production environment with privacy enabled
        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = True
        mock_settings.ENVIRONMENT = "production"

        ctx = {"validated_request": mock_validated_request, "session": mock_session, "user": mock_user}

        result = await step_6__privacy_check(ctx=ctx)

        # Should enable anonymization in production
        assert result["privacy_enabled"] is True
        assert result["environment"] == "production"

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.config.settings")
    async def test_step_6_user_specific_privacy_preferences(
        self, mock_settings, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request
    ):
        """Test Step 6: User-specific privacy preferences"""
        from app.orchestrators.privacy import step_6__privacy_check

        # Global setting disabled but user has specific preference
        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = False

        # User with privacy preference
        mock_user.privacy_settings = {"anonymize_requests": True}

        ctx = {"validated_request": mock_validated_request, "session": mock_session, "user": mock_user}

        result = await step_6__privacy_check(ctx=ctx)

        # Should respect user preference over global setting
        assert result["privacy_enabled"] is True
        assert result["user_preference_override"] is True
        assert result["next_step"] == "AnonymizeText"

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.config.settings")
    async def test_step_6_ready_for_step_7_or_8(
        self, mock_settings, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request
    ):
        """Test Step 6: Output ready for Step 7 (AnonymizeText) or Step 8 (InitAgent)"""
        from app.orchestrators.privacy import step_6__privacy_check

        # Test route to Step 7
        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = True

        ctx = {"validated_request": mock_validated_request, "session": mock_session, "user": mock_user}

        result = await step_6__privacy_check(ctx=ctx)

        # Verify output is ready for Step 7
        assert result["ready_for_anonymization"] is True
        assert result["next_step"] == "AnonymizeText"
        assert "validated_request" in result
        assert "session" in result
        assert "user" in result

        # Test route to Step 8
        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = False

        result = await step_6__privacy_check(ctx=ctx)

        # Verify output is ready for Step 8
        assert result["ready_for_workflow_init"] is True
        assert result["next_step"] == "InitAgent"

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.config.settings")
    async def test_step_6_comprehensive_logging(
        self, mock_settings, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request
    ):
        """Test Step 6: Comprehensive logging format"""
        from app.orchestrators.privacy import step_6__privacy_check

        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = True

        ctx = {
            "validated_request": mock_validated_request,
            "session": mock_session,
            "user": mock_user,
            "request_metadata": {"request_id": "req_comprehensive"},
        }

        await step_6__privacy_check(ctx=ctx)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            "step",
            "step_id",
            "node_label",
            "privacy_enabled",
            "anonymization_required",
            "decision",
            "processing_stage",
            "next_step",
            "session_id",
            "user_id",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]["step"] == 6
        assert log_call[1]["step_id"] == "RAG.privacy.privacy.anonymize.requests.enabled"
        assert log_call[1]["node_label"] == "PrivacyCheck"

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.config.settings")
    async def test_step_6_performance_tracking(self, mock_settings, mock_logger, mock_rag_log, mock_validated_request):
        """Test Step 6: Performance tracking with timer"""
        from app.orchestrators.privacy import step_6__privacy_check

        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = True

        with patch("app.orchestrators.privacy.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            ctx = {"validated_request": mock_validated_request}
            await step_6__privacy_check(ctx=ctx)

            # Verify timer was used
            mock_timer.assert_called_with(
                6, "RAG.privacy.privacy.anonymize.requests.enabled", "PrivacyCheck", stage="start"
            )

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.config.settings")
    async def test_step_6_decision_branching(
        self, mock_settings, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request
    ):
        """Test Step 6: Proper decision branching logic"""
        from app.orchestrators.privacy import step_6__privacy_check

        ctx = {"validated_request": mock_validated_request, "session": mock_session, "user": mock_user}

        # Test anonymization enabled branch
        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = True
        result = await step_6__privacy_check(ctx=ctx)

        assert result["decision"] == "anonymize_enabled"
        assert result["next_step"] == "AnonymizeText"
        assert result["ready_for_anonymization"] is True
        assert result["ready_for_workflow_init"] is False

        # Test anonymization disabled branch
        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = False
        result = await step_6__privacy_check(ctx=ctx)

        assert result["decision"] == "anonymize_disabled"
        assert result["next_step"] == "InitAgent"
        assert result["ready_for_anonymization"] is False
        assert result["ready_for_workflow_init"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.privacy.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.config.settings")
    async def test_step_6_parity_preservation(
        self, mock_settings, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request
    ):
        """Test Step 6: Parity test - behavior identical to ChatbotController.chat privacy check"""
        from app.orchestrators.privacy import step_6__privacy_check

        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = True

        ctx = {"validated_request": mock_validated_request, "session": mock_session, "user": mock_user}

        result = await step_6__privacy_check(ctx=ctx)

        # Verify behavior matches ChatbotController.chat privacy logic
        assert result["privacy_enabled"] == mock_settings.PRIVACY_ANONYMIZE_REQUESTS
        assert result["anonymization_required"] is True
        assert result["next_step"] == "AnonymizeText"

        # Verify data is preserved for next step
        assert result["validated_request"] == mock_validated_request
        assert result["session"] == mock_session
        assert result["user"] == mock_user
