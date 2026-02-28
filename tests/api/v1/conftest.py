"""Conftest for API v1 tests - ensures DB env vars are set before app imports."""

import os

if not os.environ.get("POSTGRES_URL"):
    os.environ["POSTGRES_URL"] = "postgresql://test:test@localhost:5432/pratikoai_test"
