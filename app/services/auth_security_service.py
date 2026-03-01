"""Auth security service for lockout, session limits, and login attempt tracking (P1/P2/P3)."""

from datetime import UTC, datetime, timedelta

from app.core.logging import logger


class AuthSecurityService:
    """Centralized auth security logic: lockout, session limits, audit."""

    MAX_FAILED_ATTEMPTS = 5
    BASE_LOCKOUT_MINUTES = 15
    MAX_LOCKOUT_HOURS = 24

    def __init__(self, max_sessions: int = 5):
        self.max_sessions = max_sessions

    # -- Account lockout (P1) --

    def is_account_locked(self, account_locked_until: datetime | None) -> bool:
        """Check if an account is currently locked.

        Args:
            account_locked_until: The lockout expiry timestamp (None = not locked)

        Returns:
            True if the account is locked
        """
        if account_locked_until is None:
            return False
        now = datetime.now(UTC)
        locked_until = (
            account_locked_until.replace(tzinfo=UTC) if account_locked_until.tzinfo is None else account_locked_until
        )
        return now < locked_until

    def should_lock_account(self, failed_attempts: int) -> bool:
        """Check if the account should be locked based on failed attempt count.

        Args:
            failed_attempts: Number of consecutive failed attempts

        Returns:
            True if the account should be locked
        """
        return failed_attempts >= self.MAX_FAILED_ATTEMPTS

    def get_lockout_duration(self, failed_attempts: int) -> timedelta:
        """Calculate lockout duration with exponential backoff.

        - 5 attempts: 15 minutes
        - 10 attempts: 30 minutes
        - 15 attempts: 60 minutes
        - Capped at 24 hours

        Args:
            failed_attempts: Number of consecutive failed attempts

        Returns:
            Lockout duration
        """
        # How many times the threshold has been reached
        multiplier = max(1, failed_attempts // self.MAX_FAILED_ATTEMPTS)
        minutes = self.BASE_LOCKOUT_MINUTES * multiplier
        duration = timedelta(minutes=minutes)
        max_duration = timedelta(hours=self.MAX_LOCKOUT_HOURS)
        result = min(duration, max_duration)
        logger.info(
            "lockout_duration_calculated",
            failed_attempts=failed_attempts,
            duration_minutes=result.total_seconds() / 60,
        )
        return result

    # -- Session limits (P3) --

    def exceeds_session_limit(self, current_count: int) -> bool:
        """Check if user has reached the concurrent session limit.

        Args:
            current_count: Current number of active sessions

        Returns:
            True if the limit is exceeded
        """
        return current_count >= self.max_sessions


# Global instance
auth_security_service = AuthSecurityService()
