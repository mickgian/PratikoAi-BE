"""Tests for dev-to-QA knowledge data sync script.

Validates the sync utility functions: row data preparation,
column extraction, and table sync logic with ON CONFLICT DO NOTHING.
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from scripts.sync_dev_to_qa import (
    SYNC_TABLES,
    prepare_row_data,
)


class TestPrepareRowData:
    """Test row data type conversion for cross-DB transfer."""

    def test_preserves_none_values(self):
        row = {"id": 1, "title": None, "content": None}
        result = prepare_row_data(row)
        assert result["title"] is None
        assert result["content"] is None

    def test_converts_dict_to_json_string(self):
        row = {"id": 1, "metadata": {"key": "value", "nested": [1, 2]}}
        result = prepare_row_data(row)
        assert result["metadata"] == json.dumps({"key": "value", "nested": [1, 2]})

    def test_converts_list_to_json_string(self):
        row = {"id": 1, "tags": ["tax", "iva", "inps"]}
        result = prepare_row_data(row)
        assert result["tags"] == json.dumps(["tax", "iva", "inps"])

    def test_converts_decimal_to_float(self):
        row = {"id": 1, "score": Decimal("0.85"), "amount": Decimal("1234.56")}
        result = prepare_row_data(row)
        assert result["score"] == 0.85
        assert result["amount"] == 1234.56
        assert isinstance(result["score"], float)

    def test_preserves_primitive_types(self):
        row = {"id": 1, "title": "Test", "count": 42, "active": True, "score": 0.5}
        result = prepare_row_data(row)
        assert result == row

    def test_handles_empty_dict(self):
        assert prepare_row_data({}) == {}

    def test_handles_mixed_types(self):
        row = {
            "id": 1,
            "title": "Circolare INPS",
            "metadata": {"source": "inps"},
            "score": Decimal("0.9"),
            "tags": ["circolari"],
            "content": None,
        }
        result = prepare_row_data(row)
        assert result["id"] == 1
        assert result["title"] == "Circolare INPS"
        assert result["metadata"] == '{"source": "inps"}'
        assert result["score"] == 0.9
        assert result["tags"] == '["circolari"]'
        assert result["content"] is None


class TestSyncTableConfig:
    """Test sync table configuration."""

    def test_four_tables_defined(self):
        assert len(SYNC_TABLES) == 4

    def test_dependency_order(self):
        """Tables must be synced in dependency order: parents before children."""
        table_names = [t["name"] for t in SYNC_TABLES]
        # feed_status has no dependencies
        # knowledge_items must come before knowledge_chunks (FK)
        # regulatory_documents references knowledge_items
        ki_idx = table_names.index("knowledge_items")
        kc_idx = table_names.index("knowledge_chunks")
        rd_idx = table_names.index("regulatory_documents")
        assert ki_idx < kc_idx, "knowledge_items must sync before knowledge_chunks"
        assert ki_idx < rd_idx, "knowledge_items must sync before regulatory_documents"

    def test_all_tables_have_required_config(self):
        required_keys = {"name", "label", "skip_columns", "conflict_column", "conflict_action"}
        for table in SYNC_TABLES:
            missing = required_keys - set(table.keys())
            assert not missing, f"Table {table['name']} missing config keys: {missing}"

    def test_search_vector_excluded_from_knowledge_tables(self):
        """search_vector is auto-maintained by DB trigger — must not be copied."""
        for table in SYNC_TABLES:
            if table["name"] in ("knowledge_items", "knowledge_chunks"):
                assert "search_vector" in table["skip_columns"], f"{table['name']} must skip search_vector column"

    def test_conflict_action_is_do_nothing(self):
        """ON CONFLICT DO NOTHING preserves existing QA state."""
        for table in SYNC_TABLES:
            assert table["conflict_action"] == "DO NOTHING", (
                f"{table['name']} must use DO NOTHING to preserve QA state"
            )
