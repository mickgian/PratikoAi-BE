"""Tests for DEV-368: Pagination Standardization."""

import pytest
from pydantic import ValidationError

from app.schemas.pagination import PaginatedResponse, PaginationParams


class TestPaginationParams:
    """Tests for PaginationParams schema."""

    def test_defaults(self):
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_custom_values(self):
        params = PaginationParams(page=3, page_size=50)
        assert params.page == 3
        assert params.page_size == 50

    def test_offset_calculation(self):
        params = PaginationParams(page=1, page_size=20)
        assert params.offset == 0

        params = PaginationParams(page=2, page_size=20)
        assert params.offset == 20

        params = PaginationParams(page=3, page_size=10)
        assert params.offset == 20

    def test_page_zero_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_negative_page_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(page=-1)

    def test_page_size_zero_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(page_size=0)

    def test_page_size_over_100_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(page_size=101)

    def test_page_size_max_100(self):
        params = PaginationParams(page_size=100)
        assert params.page_size == 100


class TestPaginatedResponse:
    """Tests for PaginatedResponse wrapper."""

    def test_valid_response(self):
        resp = PaginatedResponse[str](
            items=["a", "b"],
            total=10,
            page=1,
            page_size=2,
            total_pages=5,
        )
        assert resp.items == ["a", "b"]
        assert resp.total == 10
        assert resp.page == 1
        assert resp.total_pages == 5

    def test_empty_items(self):
        resp = PaginatedResponse[str](
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert resp.items == []
        assert resp.total == 0

    def test_negative_total_rejected(self):
        with pytest.raises(ValidationError):
            PaginatedResponse[str](
                items=[],
                total=-1,
                page=1,
                page_size=20,
                total_pages=0,
            )
