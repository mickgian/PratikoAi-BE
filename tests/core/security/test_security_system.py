"""Comprehensive tests for the enhanced security system."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.security import api_key_manager, request_signer, security_audit_logger, security_monitor
from app.core.security.audit_logger import SecurityEventType, SecuritySeverity
from app.core.security.security_monitor import ResponseAction, ThreatLevel


class TestAPIKeyRotationManager:
    """Test API key rotation functionality."""

    def test_generate_api_key_user_type(self):
        """Test generating user API key."""
        user_id = "test_user_123"
        api_key = api_key_manager.generate_api_key(user_id, "user")

        assert api_key.startswith("nai_user_")
        assert len(api_key) > 20

    def test_generate_api_key_admin_type(self):
        """Test generating admin API key."""
        user_id = "admin_user_123"
        api_key = api_key_manager.generate_api_key(user_id, "admin")

        assert api_key.startswith("nai_admin_")
        assert len(api_key) > 20

    def test_generate_api_key_service_type(self):
        """Test generating service API key."""
        service_id = "service_123"
        api_key = api_key_manager.generate_api_key(service_id, "service")

        assert api_key.startswith("nai_svc_")
        assert len(api_key) > 20

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "nai_user_test_key_12345"
        hash1 = api_key_manager.hash_api_key(api_key)
        hash2 = api_key_manager.hash_api_key(api_key)

        assert hash1 == hash2  # Consistent hashing
        assert len(hash1) == 64  # SHA-256 hex length
        assert hash1 != api_key  # Different from original

    @pytest.mark.asyncio
    async def test_store_api_key_success(self):
        """Test successful API key storage."""
        user_id = "test_user"
        api_key = "nai_user_test_key"

        result = await api_key_manager.store_api_key(user_id, api_key)
        assert result is True

    @pytest.mark.asyncio
    async def test_rotate_user_keys(self):
        """Test user key rotation."""
        user_id = "test_user"

        with patch.object(api_key_manager, "_get_active_keys", return_value=["old_key_1", "old_key_2"]):
            with patch.object(api_key_manager, "store_api_key", return_value=True):
                with patch.object(api_key_manager, "_deprecate_keys", return_value=True):
                    result = await api_key_manager.rotate_user_keys(user_id)

                    assert "new_key" in result
                    assert result["old_keys_count"] == 2
                    assert "grace_period_ends" in result
                    assert result["new_key"].startswith("nai_user_")

    @pytest.mark.asyncio
    async def test_validate_api_key_valid(self):
        """Test API key validation with valid key."""
        api_key = "nai_user_valid_key_123"

        result = await api_key_manager.validate_api_key(api_key)

        assert result is not None
        assert result["key_type"] == "user"
        assert "user_id" in result
        assert "validated_at" in result

    @pytest.mark.asyncio
    async def test_validate_api_key_admin(self):
        """Test admin API key validation."""
        api_key = "nai_admin_valid_key_123"

        result = await api_key_manager.validate_api_key(api_key)

        assert result is not None
        assert result["key_type"] == "admin"

    @pytest.mark.asyncio
    async def test_revoke_api_key(self):
        """Test API key revocation."""
        api_key = "nai_user_revoke_me"
        reason = "security_breach"

        result = await api_key_manager.revoke_api_key(api_key, reason)
        assert result is True

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self):
        """Test expired key cleanup."""
        result = await api_key_manager.cleanup_expired_keys()
        assert isinstance(result, int)
        assert result >= 0

    @pytest.mark.asyncio
    async def test_get_key_statistics(self):
        """Test key statistics retrieval."""
        stats = await api_key_manager.get_key_statistics()

        assert isinstance(stats, dict)
        assert "total_active_keys" in stats
        assert "key_types" in stats

        # Test user-specific stats
        user_stats = await api_key_manager.get_key_statistics("test_user")
        assert "user_specific" in user_stats


class TestRequestSigner:
    """Test request signing functionality."""

    def test_generate_signature(self):
        """Test signature generation."""
        method = "POST"
        path = "/api/v1/test"
        body = b'{"test": "data"}'
        timestamp = "1640995200"
        secret_key = "test_secret_key"

        signature = request_signer.generate_signature(method, path, body, timestamp, secret_key)

        assert signature.startswith("v1=")
        assert len(signature) > 10

    def test_verify_signature_valid(self):
        """Test signature verification with valid signature."""
        method = "POST"
        path = "/api/v1/test"
        body = b'{"test": "data"}'
        timestamp = str(int(datetime.utcnow().timestamp()))
        secret_key = "test_secret_key"

        # Generate signature
        signature = request_signer.generate_signature(method, path, body, timestamp, secret_key)

        # Verify signature
        is_valid = request_signer.verify_signature(method, path, body, timestamp, signature, secret_key)

        assert is_valid is True

    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature."""
        method = "POST"
        path = "/api/v1/test"
        body = b'{"test": "data"}'
        timestamp = str(int(datetime.utcnow().timestamp()))
        secret_key = "test_secret_key"
        invalid_signature = "v1=invalid_signature_hash"

        is_valid = request_signer.verify_signature(method, path, body, timestamp, invalid_signature, secret_key)

        assert is_valid is False

    def test_verify_signature_expired_timestamp(self):
        """Test signature verification with expired timestamp."""
        method = "POST"
        path = "/api/v1/test"
        body = b'{"test": "data"}'
        old_timestamp = str(int((datetime.utcnow() - timedelta(hours=1)).timestamp()))
        secret_key = "test_secret_key"

        signature = request_signer.generate_signature(method, path, body, old_timestamp, secret_key)

        is_valid = request_signer.verify_signature(method, path, body, old_timestamp, signature, secret_key)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_sign_outgoing_request(self):
        """Test signing outgoing requests."""
        method = "POST"
        url = "https://api.example.com/test?param=value"
        body = b'{"data": "test"}'

        headers = await request_signer.sign_outgoing_request(method, url, body)

        assert request_signer.signature_header in headers
        assert request_signer.timestamp_header in headers
        assert headers[request_signer.signature_header].startswith("v1=")

    def test_create_webhook_signature(self):
        """Test webhook signature creation."""
        payload = b'{"webhook": "data"}'
        secret = "webhook_secret"

        signature = request_signer.create_webhook_signature(payload, secret)

        assert signature.startswith("sha256=")
        assert len(signature) > 10

    def test_verify_webhook_signature_valid(self):
        """Test webhook signature verification."""
        payload = b'{"webhook": "data"}'
        secret = "webhook_secret"

        signature = request_signer.create_webhook_signature(payload, secret)
        is_valid = request_signer.verify_webhook_signature(payload, signature, secret)

        assert is_valid is True

    def test_verify_webhook_signature_invalid(self):
        """Test webhook signature verification with invalid signature."""
        payload = b'{"webhook": "data"}'
        secret = "webhook_secret"
        invalid_signature = "sha256=invalid_hash"

        is_valid = request_signer.verify_webhook_signature(payload, invalid_signature, secret)

        assert is_valid is False


class TestSecurityAuditLogger:
    """Test security audit logging functionality."""

    @pytest.mark.asyncio
    async def test_log_security_event_basic(self):
        """Test basic security event logging."""
        result = await security_audit_logger.log_security_event(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            severity=SecuritySeverity.LOW,
            user_id="test_user",
            ip_address="192.168.1.100",
            outcome="success",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_authentication_event_success(self):
        """Test authentication event logging."""
        result = await security_audit_logger.log_authentication_event(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            user_id="test_user",
            ip_address="192.168.1.100",
            outcome="success",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_authentication_event_failure(self):
        """Test failed authentication event logging."""
        result = await security_audit_logger.log_authentication_event(
            event_type=SecurityEventType.LOGIN_FAILURE,
            user_id="test_user",
            ip_address="192.168.1.100",
            outcome="failure",
            failure_reason="invalid_password",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_api_security_event(self):
        """Test API security event logging."""
        result = await security_audit_logger.log_api_security_event(
            event_type=SecurityEventType.API_KEY_CREATED,
            user_id="test_user",
            api_endpoint="/api/v1/security/api-keys/generate",
            api_key_prefix="nai_user_123...",
            ip_address="192.168.1.100",
            outcome="success",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_gdpr_event(self):
        """Test GDPR compliance event logging."""
        result = await security_audit_logger.log_gdpr_event(
            action="consent", user_id="test_user", data_type="personal_data", legal_basis="consent", outcome="success"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_payment_security_event(self):
        """Test payment security event logging."""
        result = await security_audit_logger.log_payment_security_event(
            event_type=SecurityEventType.PAYMENT_SUCCESS,
            user_id="test_user",
            payment_method="stripe",
            amount=69.0,
            currency="EUR",
            outcome="success",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_payment_fraud_event(self):
        """Test payment fraud event logging."""
        result = await security_audit_logger.log_payment_security_event(
            event_type=SecurityEventType.FRAUD_DETECTED,
            user_id="test_user",
            payment_method="stripe",
            amount=69.0,
            currency="EUR",
            outcome="blocked",
            fraud_score=0.95,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_get_security_events(self):
        """Test security event retrieval."""
        events = await security_audit_logger.get_security_events(user_id="test_user", limit=10)

        assert isinstance(events, list)
        if events:
            assert "timestamp" in events[0]
            assert "event_type" in events[0]

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self):
        """Test compliance report generation."""
        report = await security_audit_logger.generate_compliance_report(report_type="gdpr")

        assert isinstance(report, dict)
        assert "report_type" in report
        assert "generated_at" in report
        assert "summary" in report


class TestSecurityMonitor:
    """Test security monitoring and threat detection."""

    @pytest.mark.asyncio
    async def test_process_security_event_normal(self):
        """Test processing normal security event."""
        threat = await security_monitor.process_security_event(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            user_id="test_user",
            ip_address="192.168.1.100",
            outcome="success",
        )

        # Normal event should not trigger threat
        assert threat is None

    @pytest.mark.asyncio
    async def test_process_security_event_brute_force(self):
        """Test brute force attack detection."""
        ip_address = "192.168.1.100"

        # Simulate multiple failed login attempts
        for _i in range(6):  # Threshold is 5
            threat = await security_monitor.process_security_event(
                event_type=SecurityEventType.LOGIN_FAILURE, ip_address=ip_address, outcome="failure"
            )

        # Should detect threat after threshold
        assert threat is not None
        assert threat.threat_type == "brute_force_login"
        assert threat.level == ThreatLevel.HIGH

    @pytest.mark.asyncio
    async def test_process_security_event_invalid_api_key_spam(self):
        """Test invalid API key spam detection."""
        ip_address = "192.168.1.101"

        # Simulate multiple invalid API key attempts
        for _i in range(11):  # Threshold is 10
            threat = await security_monitor.process_security_event(
                event_type=SecurityEventType.INVALID_API_KEY, ip_address=ip_address, outcome="invalid"
            )

        # Should detect threat after threshold
        assert threat is not None
        assert threat.threat_type == "invalid_api_key_spam"
        assert threat.level == ThreatLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_process_security_event_signature_failures(self):
        """Test signature failure detection."""
        ip_address = "192.168.1.102"

        # Simulate multiple signature failures
        for _i in range(21):  # Threshold is 20
            threat = await security_monitor.process_security_event(
                event_type=SecurityEventType.SIGNATURE_FAILED, ip_address=ip_address, outcome="invalid_signature"
            )

        # Should detect threat after threshold
        assert threat is not None
        assert threat.threat_type == "signature_failures"
        assert threat.level == ThreatLevel.HIGH

    def test_is_ip_blocked(self):
        """Test IP blocking check."""
        test_ip = "192.168.1.200"

        # Initially not blocked
        assert security_monitor.is_ip_blocked(test_ip) is False

        # Add to blocked IPs
        security_monitor.blocked_ips.add(test_ip)
        assert security_monitor.is_ip_blocked(test_ip) is True

        # Clean up
        security_monitor.blocked_ips.remove(test_ip)

    def test_is_user_blocked(self):
        """Test user blocking check."""
        test_user = "blocked_user"

        # Initially not blocked
        assert security_monitor.is_user_blocked(test_user) is False

        # Add to blocked users
        security_monitor.blocked_users.add(test_user)
        assert security_monitor.is_user_blocked(test_user) is True

        # Clean up
        security_monitor.blocked_users.remove(test_user)

    def test_is_rate_limited(self):
        """Test rate limiting check."""
        test_ip = "192.168.1.201"

        # Initially not rate limited
        assert security_monitor.is_rate_limited(test_ip) is False

        # Add rate limit
        security_monitor.rate_limited_ips[test_ip] = {
            "count": 0,  # Exhausted
            "reset_time": datetime.utcnow() + timedelta(minutes=10),
        }
        assert security_monitor.is_rate_limited(test_ip) is True

        # Test expired rate limit
        security_monitor.rate_limited_ips[test_ip]["reset_time"] = datetime.utcnow() - timedelta(minutes=1)
        assert security_monitor.is_rate_limited(test_ip) is False

    def test_get_threat_statistics(self):
        """Test threat statistics retrieval."""
        stats = security_monitor.get_threat_statistics()

        assert isinstance(stats, dict)
        assert "monitoring_status" in stats
        assert "active_threats" in stats
        assert "blocked_ips" in stats
        assert "blocked_users" in stats
        assert "security_rules_count" in stats

    @pytest.mark.asyncio
    async def test_resolve_threat(self):
        """Test threat resolution."""
        # Create a mock threat
        threat_id = "test_threat_123"
        from app.core.security.security_monitor import SecurityThreat

        mock_threat = SecurityThreat(
            threat_id=threat_id,
            threat_type="test_threat",
            level=ThreatLevel.MEDIUM,
            source_ip="192.168.1.100",
            user_id="test_user",
            description="Test threat",
            evidence={},
            detected_at=datetime.utcnow(),
            response_actions=[ResponseAction.LOG_ONLY],
        )

        # Add to active threats
        security_monitor.active_threats[threat_id] = mock_threat

        # Resolve the threat
        result = await security_monitor.resolve_threat(threat_id, "False positive")

        assert result is True
        assert security_monitor.active_threats[threat_id].resolved is True

        # Clean up
        del security_monitor.active_threats[threat_id]


class TestSecurityIntegration:
    """Test integration between security components."""

    @pytest.mark.asyncio
    async def test_end_to_end_threat_detection_and_logging(self):
        """Test complete threat detection and audit logging flow."""
        ip_address = "192.168.1.300"

        # Simulate brute force attack
        for _i in range(6):
            threat = await security_monitor.process_security_event(
                event_type=SecurityEventType.LOGIN_FAILURE, ip_address=ip_address, outcome="failure"
            )

        # Should detect threat
        assert threat is not None

        # Check that IP is blocked
        assert security_monitor.is_ip_blocked(ip_address) is True

        # Resolve threat
        result = await security_monitor.resolve_threat(threat.threat_id)
        assert result is True

        # Clean up
        security_monitor.blocked_ips.discard(ip_address)
        if threat.threat_id in security_monitor.active_threats:
            del security_monitor.active_threats[threat.threat_id]

    @pytest.mark.asyncio
    async def test_api_key_rotation_with_audit_logging(self):
        """Test API key rotation with proper audit logging."""
        user_id = "test_user_rotation"

        with patch.object(api_key_manager, "_get_active_keys", return_value=[]):
            with patch.object(api_key_manager, "store_api_key", return_value=True):
                with patch.object(api_key_manager, "_deprecate_keys", return_value=True):
                    # Rotate keys
                    result = await api_key_manager.rotate_user_keys(user_id)

                    assert "new_key" in result
                    assert result["new_key"].startswith("nai_user_")

    def test_request_signing_with_security_monitoring(self):
        """Test request signing integration with security monitoring."""
        method = "POST"
        path = "/api/v1/test"
        body = b'{"test": "data"}'
        timestamp = str(int(datetime.utcnow().timestamp()))
        secret_key = "test_secret"

        # Generate and verify signature
        signature = request_signer.generate_signature(method, path, body, timestamp, secret_key)
        is_valid = request_signer.verify_signature(method, path, body, timestamp, signature, secret_key)

        assert is_valid is True

        # Test invalid signature (should trigger security event in production)
        invalid_signature = "v1=invalid"
        is_valid = request_signer.verify_signature(method, path, body, timestamp, invalid_signature, secret_key)

        assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
