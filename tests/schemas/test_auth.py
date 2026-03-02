"""Tests for auth schemas (new P0-P2 schemas)."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    EmailOTPRequest,
    EmailVerificationRequest,
    LoginResponse,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    ResendVerificationRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TwoFactorBackupRequest,
    TwoFactorVerifyRequest,
)


class TestPasswordResetRequest:
    """Test PasswordResetRequest schema."""

    def test_valid_email(self):
        req = PasswordResetRequest(email="test@example.com")
        assert req.email == "test@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            PasswordResetRequest(email="not-an-email")


class TestPasswordResetConfirm:
    """Test PasswordResetConfirm schema."""

    def test_valid_reset(self):
        req = PasswordResetConfirm(token="abc123", new_password="Strong1!pass")
        assert req.token == "abc123"

    def test_weak_password_rejected(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirm(token="abc123", new_password="weak")

    def test_password_no_uppercase(self):
        with pytest.raises(ValidationError, match="maiuscola"):
            PasswordResetConfirm(token="abc", new_password="nouppercase1!")

    def test_password_no_number(self):
        with pytest.raises(ValidationError, match="numero"):
            PasswordResetConfirm(token="abc", new_password="NoNumber!abc")

    def test_password_no_special(self):
        with pytest.raises(ValidationError, match="speciale"):
            PasswordResetConfirm(token="abc", new_password="NoSpecial1abc")


class TestEmailVerificationRequest:
    """Test EmailVerificationRequest schema."""

    def test_valid_token(self):
        req = EmailVerificationRequest(token="verify-token-123")
        assert req.token == "verify-token-123"


class TestResendVerificationRequest:
    """Test ResendVerificationRequest schema."""

    def test_valid_email(self):
        req = ResendVerificationRequest(email="test@example.com")
        assert req.email == "test@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            ResendVerificationRequest(email="bad")


class TestLoginResponse:
    """Test LoginResponse schema."""

    def test_normal_login(self):
        resp = LoginResponse(
            access_token="tok",
            refresh_token="ref",
            requires_2fa=False,
        )
        assert resp.requires_2fa is False
        assert resp.access_token == "tok"

    def test_2fa_required(self):
        resp = LoginResponse(
            requires_2fa=True,
            two_factor_token="tmp-token",
        )
        assert resp.requires_2fa is True
        assert resp.access_token == ""


class TestTOTPSetupResponse:
    """Test TOTPSetupResponse schema."""

    def test_valid_setup(self):
        resp = TOTPSetupResponse(
            secret="JBSWY3DPEHPK3PXP",
            provisioning_uri="otpauth://totp/PratikoAI:test@example.com?secret=JBSWY3DPEHPK3PXP",
            backup_codes=["abcd-efgh", "ijkl-mnop"],
        )
        assert len(resp.backup_codes) == 2


class TestTOTPVerifyRequest:
    """Test TOTPVerifyRequest schema."""

    def test_valid_code(self):
        req = TOTPVerifyRequest(code="123456")
        assert req.code == "123456"

    def test_short_code_rejected(self):
        with pytest.raises(ValidationError):
            TOTPVerifyRequest(code="123")

    def test_long_code_rejected(self):
        with pytest.raises(ValidationError):
            TOTPVerifyRequest(code="1234567")


class TestTwoFactorVerifyRequest:
    """Test TwoFactorVerifyRequest schema."""

    def test_valid(self):
        req = TwoFactorVerifyRequest(two_factor_token="tmp", code="654321")
        assert req.two_factor_token == "tmp"
        assert req.code == "654321"


class TestTwoFactorBackupRequest:
    """Test TwoFactorBackupRequest schema."""

    def test_valid(self):
        req = TwoFactorBackupRequest(two_factor_token="tmp", backup_code="abcd-efgh")
        assert req.backup_code == "abcd-efgh"


class TestEmailOTPRequest:
    """Test EmailOTPRequest schema."""

    def test_valid(self):
        req = EmailOTPRequest(two_factor_token="tmp")
        assert req.two_factor_token == "tmp"


class TestMessageResponse:
    """Test MessageResponse schema."""

    def test_valid(self):
        resp = MessageResponse(message="OK")
        assert resp.message == "OK"
