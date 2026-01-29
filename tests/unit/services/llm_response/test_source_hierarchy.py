"""Tests for source hierarchy ranking functions."""

import pytest

from app.services.llm_response.constants import SOURCE_HIERARCHY
from app.services.llm_response.source_hierarchy import apply_source_hierarchy


class TestApplySourceHierarchy:
    """Tests for apply_source_hierarchy function."""

    def test_ranks_legge_highest(self):
        """Happy path: Legge sources get rank 1 (highest authority)."""
        sources = [{"ref": "Legge 123/2024"}]

        result = apply_source_hierarchy(sources)

        assert result[0]["hierarchy_rank"] == SOURCE_HIERARCHY["legge"]

    def test_ranks_decreto_second(self):
        """Decreto sources get rank 2."""
        sources = [{"ref": "D.Lgs. 81/2008"}]

        result = apply_source_hierarchy(sources)

        assert result[0]["hierarchy_rank"] == SOURCE_HIERARCHY["decreto"]

    def test_ranks_circolare_third(self):
        """Circolare sources get rank 3."""
        sources = [{"ref": "Circolare AdE 15/E"}]

        result = apply_source_hierarchy(sources)

        assert result[0]["hierarchy_rank"] == SOURCE_HIERARCHY["circolare"]

    def test_ranks_interpello_fourth(self):
        """Interpello sources get rank 4."""
        sources = [{"ref": "Interpello n. 42/2024"}]

        result = apply_source_hierarchy(sources)

        assert result[0]["hierarchy_rank"] == SOURCE_HIERARCHY["interpello"]

    def test_ranks_prassi_fifth(self):
        """Prassi sources get rank 5."""
        sources = [{"ref": "Risoluzione 100/E"}]

        result = apply_source_hierarchy(sources)

        assert result[0]["hierarchy_rank"] == SOURCE_HIERARCHY["prassi"]

    def test_sorts_by_hierarchy_rank(self):
        """Sources are sorted by hierarchy rank (highest authority first)."""
        sources = [
            {"ref": "Interpello 42/2024"},
            {"ref": "Legge 123/2024"},
            {"ref": "Circolare 15/E"},
        ]

        result = apply_source_hierarchy(sources)

        assert result[0]["ref"] == "Legge 123/2024"
        assert result[1]["ref"] == "Circolare 15/E"
        assert result[2]["ref"] == "Interpello 42/2024"

    def test_returns_empty_list_for_empty_input(self):
        """Edge case: returns empty list for empty input."""
        assert apply_source_hierarchy([]) == []
        assert apply_source_hierarchy(None) == []

    def test_assigns_unknown_rank_for_unrecognized_refs(self):
        """Unrecognized references get unknown rank (99)."""
        sources = [{"ref": "Unknown document type"}]

        result = apply_source_hierarchy(sources)

        assert result[0]["hierarchy_rank"] == SOURCE_HIERARCHY["unknown"]

    def test_handles_l_abbreviation_for_legge(self):
        """Recognizes 'L.' abbreviation for Legge."""
        sources = [{"ref": "L. 190/2012"}]

        result = apply_source_hierarchy(sources)

        assert result[0]["hierarchy_rank"] == SOURCE_HIERARCHY["legge"]

    def test_handles_dpr_as_decreto(self):
        """Recognizes DPR as decreto type."""
        sources = [{"ref": "DPR 600/1973"}]

        result = apply_source_hierarchy(sources)

        assert result[0]["hierarchy_rank"] == SOURCE_HIERARCHY["decreto"]

    def test_preserves_original_source_fields(self):
        """Original source fields are preserved after ranking."""
        sources = [{"ref": "Legge 123/2024", "title": "Tax Law", "page": 42}]

        result = apply_source_hierarchy(sources)

        assert result[0]["ref"] == "Legge 123/2024"
        assert result[0]["title"] == "Tax Law"
        assert result[0]["page"] == 42
