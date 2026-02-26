"""DEV-394: Feature Flag Infrastructure — Global and per-studio flags.

Provides a feature flag system with:
- Global flags (all studios)
- Per-studio overrides (take precedence over global)
- Environment variable defaults (FF_<FLAG_NAME> env vars)
- Percentage-based rollout
- Audit logging of changes
"""

import hashlib
import os
import re
from datetime import UTC, datetime, timezone
from uuid import UUID

from app.core.logging import logger

# Flag name validation: only lowercase alphanumeric, hyphens, underscores
_FLAG_NAME_RE = re.compile(r"^[a-z0-9_-]+$")


class FeatureFlagService:
    """In-memory feature flag service with env var fallback.

    For production use, this should be backed by Redis for caching
    and persistence.  The in-memory implementation suffices for
    single-process deployments and testing.
    """

    def __init__(self) -> None:
        self._global_flags: dict[str, bool] = {}
        self._studio_flags: dict[str, dict[str, bool]] = {}  # flag_name -> {studio_id_str: bool}
        self._percentage_rollouts: dict[str, int] = {}  # flag_name -> percentage (0-100)
        self._audit_log: dict[str, list[dict]] = {}  # flag_name -> [entries]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_flag_name(flag_name: str) -> str:
        """Validate and normalise flag name.

        Raises:
            ValueError: If flag name is empty or contains invalid chars.
        """
        name = flag_name.strip()
        if not name:
            raise ValueError("Nome flag obbligatorio")
        if not _FLAG_NAME_RE.match(name):
            raise ValueError(f"Flag '{name}' contiene caratteri non validi (ammessi: a-z 0-9 _ -)")
        return name

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def is_enabled(self, flag_name: str, studio_id: UUID | None = None) -> bool:
        """Check whether a flag is enabled.

        Resolution order:
        1. Studio-level override (if studio_id provided)
        2. Percentage rollout (if configured and studio_id provided)
        3. Global flag value
        4. Environment variable ``FF_<FLAG_NAME>``
        5. Default: False
        """
        name = self._validate_flag_name(flag_name)

        # 1. Studio override
        if studio_id is not None:
            sid = str(studio_id)
            studio_overrides = self._studio_flags.get(name, {})
            if sid in studio_overrides:
                return studio_overrides[sid]

        # 2. Percentage rollout
        if name in self._percentage_rollouts and studio_id is not None:
            pct = self._percentage_rollouts[name]
            if pct <= 0:
                return False
            if pct >= 100:
                # Still need global to be True for rollout to apply
                if name in self._global_flags:
                    return self._global_flags[name]
                return True
            # Hash-based deterministic bucketing
            bucket = self._studio_bucket(name, studio_id)
            return bucket < pct

        # 3. Global flag
        if name in self._global_flags:
            return self._global_flags[name]

        # 4. Environment variable fallback
        env_key = f"FF_{name.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val.lower() in ("true", "1", "yes")

        # 5. Safe default
        return False

    def set_global_flag(self, flag_name: str, enabled: bool) -> None:
        """Set a global feature flag."""
        name = self._validate_flag_name(flag_name)
        self._global_flags[name] = enabled
        self._record_audit(name, enabled, scope="global")
        logger.info("feature_flag_set", flag_name=name, enabled=enabled, scope="global")

    def set_studio_flag(self, flag_name: str, studio_id: UUID, enabled: bool) -> None:
        """Set a per-studio feature flag override."""
        name = self._validate_flag_name(flag_name)
        sid = str(studio_id)
        if name not in self._studio_flags:
            self._studio_flags[name] = {}
        self._studio_flags[name][sid] = enabled
        self._record_audit(name, enabled, scope="studio", studio_id=sid)
        logger.info("feature_flag_set", flag_name=name, enabled=enabled, scope="studio", studio_id=sid)

    def remove_studio_flag(self, flag_name: str, studio_id: UUID) -> None:
        """Remove a per-studio override (inherits global)."""
        name = self._validate_flag_name(flag_name)
        sid = str(studio_id)
        studio_overrides = self._studio_flags.get(name, {})
        studio_overrides.pop(sid, None)
        self._record_audit(name, None, scope="studio_removed", studio_id=sid)
        logger.info("feature_flag_removed", flag_name=name, scope="studio", studio_id=sid)

    def set_percentage_rollout(self, flag_name: str, percentage: int) -> None:
        """Set percentage-based rollout for a flag (0–100)."""
        name = self._validate_flag_name(flag_name)
        pct = max(0, min(100, percentage))
        self._percentage_rollouts[name] = pct
        self._record_audit(name, pct, scope="percentage_rollout")
        logger.info("feature_flag_rollout", flag_name=name, percentage=pct)

    def list_flags(self) -> dict:
        """Return all configured flags with their state."""
        result: dict[str, dict] = {}
        all_names = set(self._global_flags.keys()) | set(self._studio_flags.keys())
        for name in sorted(all_names):
            result[name] = {
                "global": self._global_flags.get(name),
                "studio_overrides": dict(self._studio_flags.get(name, {})),
                "percentage_rollout": self._percentage_rollouts.get(name),
            }
        return result

    def get_audit_log(self, flag_name: str) -> list[dict]:
        """Return audit log entries for a flag."""
        name = self._validate_flag_name(flag_name)
        return list(self._audit_log.get(name, []))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _studio_bucket(flag_name: str, studio_id: UUID) -> int:
        """Deterministic hash bucket (0–99) for percentage rollout."""
        key = f"{flag_name}:{studio_id}"
        digest = hashlib.md5(key.encode()).hexdigest()  # noqa: S324
        return int(digest, 16) % 100

    def _record_audit(
        self,
        flag_name: str,
        value: bool | int | None,
        scope: str,
        studio_id: str | None = None,
    ) -> None:
        """Record a flag change in the audit log."""
        if flag_name not in self._audit_log:
            self._audit_log[flag_name] = []
        entry: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "scope": scope,
            "value": value,
        }
        if studio_id is not None:
            entry["studio_id"] = studio_id
        self._audit_log[flag_name].append(entry)


# Module-level singleton
feature_flag_service = FeatureFlagService()
