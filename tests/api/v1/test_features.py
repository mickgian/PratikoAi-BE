"""Tests for features API endpoint.

TDD: Tests written FIRST before implementation.
Verifies the GET /api/v1/features endpoint returns feature flags.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with the features router."""
    from fastapi import FastAPI

    from app.api.v1.features import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


class TestFeaturesEndpoint:
    """Tests for GET /api/v1/features."""

    def test_returns_200(self, client: TestClient) -> None:
        """Happy path: endpoint returns 200 with feature flags."""
        response = client.get("/api/v1/features")
        assert response.status_code == 200

    def test_returns_features_dict(self, client: TestClient) -> None:
        """Response contains 'features' key with boolean values."""
        response = client.get("/api/v1/features")
        data = response.json()

        assert "features" in data
        assert isinstance(data["features"], dict)
        # All feature values should be booleans
        for key, value in data["features"].items():
            assert isinstance(value, bool), f"Feature '{key}' is not bool: {type(value)}"

    def test_returns_environment(self, client: TestClient) -> None:
        """Response includes the current environment name."""
        response = client.get("/api/v1/features")
        data = response.json()

        assert "environment" in data
        assert isinstance(data["environment"], str)

    def test_contains_expected_flags(self, client: TestClient) -> None:
        """Response contains the core feature flags."""
        response = client.get("/api/v1/features")
        features = response.json()["features"]

        expected_keys = {
            "web_verification",
            "query_normalization",
            "cache",
            "ocr",
            "content_structure_validation",
        }
        assert expected_keys.issubset(features.keys()), f"Missing keys: {expected_keys - features.keys()}"

    def test_no_auth_required(self, client: TestClient) -> None:
        """Features endpoint is public - no auth header needed."""
        # No Authorization header
        response = client.get("/api/v1/features")
        assert response.status_code == 200
