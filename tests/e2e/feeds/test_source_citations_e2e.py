"""
Source Citations Unit Tests

Verifies the RSS feed configuration and citation URL handling.
These tests verify the feed configuration in code without requiring database.

DEV-005: Investigate & Fix Source Citations for All RSS Feed Sources
"""

import pytest


class TestFeedSourceConfiguration:
    """Tests that verify RSS feed source configuration in the codebase."""

    def test_all_expected_sources_defined_in_migration(self):
        """Verify all expected sources are defined in the migration file."""
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "alembic",
            "versions",
            "20251204_add_expanded_rss_feeds.py",
        )

        if not os.path.exists(migration_path):
            pytest.skip("Migration file not found")

        # Read and check the migration content
        with open(migration_path) as f:
            content = f.read()

        # Expected sources that should be in the migration
        expected_sources = [
            "agenzia_entrate",
            "inps",
            "inail",
            "gazzetta_ufficiale",
            "ministero_lavoro",
            "ministero_economia",
        ]

        for source in expected_sources:
            assert source in content, (
                f"Source '{source}' not found in migration file"
            )

    def test_inail_feeds_configured_in_migration(self):
        """Verify INAIL feeds are properly configured in migration."""
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "alembic",
            "versions",
            "20251204_add_expanded_rss_feeds.py",
        )

        if not os.path.exists(migration_path):
            pytest.skip("Migration file not found")

        with open(migration_path) as f:
            content = f.read()

        # INAIL should have feeds configured
        assert "inail.it" in content, (
            "INAIL feeds (inail.it) not found in migration"
        )
        assert "inail" in content.lower(), (
            "INAIL source not found in migration"
        )

    @pytest.mark.parametrize(
        "source,expected_domain",
        [
            ("agenzia_entrate", "agenziaentrate.gov.it"),
            ("inps", "inps.it"),
            ("inail", "inail.it"),
            ("gazzetta_ufficiale", "gazzettaufficiale.it"),
            ("ministero_lavoro", "lavoro.gov.it"),
        ],
    )
    def test_source_domains_in_migration(self, source: str, expected_domain: str):
        """Verify each source has the expected domain in migration."""
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "alembic",
            "versions",
            "20251204_add_expanded_rss_feeds.py",
        )

        if not os.path.exists(migration_path):
            pytest.skip("Migration file not found")

        with open(migration_path) as f:
            content = f.read()

        assert expected_domain in content, (
            f"Domain '{expected_domain}' for source '{source}' not found in migration"
        )


class TestContextBuilderIncludesSourceUrl:
    """Tests that verify source_url is included in context sent to LLM."""

    def test_context_builder_merge_includes_source_url(self):
        """Verify context_builder_merge.py includes source_url in output."""
        import os

        context_builder_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "app",
            "services",
            "context_builder_merge.py",
        )

        if not os.path.exists(context_builder_path):
            pytest.skip("context_builder_merge.py not found")

        with open(context_builder_path) as f:
            content = f.read()

        # Check that source_url is used in context building
        assert "source_url" in content or "Source URL" in content, (
            "context_builder_merge.py should include source_url for citations"
        )

    def test_knowledge_chunk_model_has_source_url_field(self):
        """Verify KnowledgeChunk model has source_url field."""
        from app.models.knowledge_chunk import KnowledgeChunk

        # Check if source_url is a field on the model
        assert hasattr(KnowledgeChunk, "source_url"), (
            "KnowledgeChunk model should have source_url field for citations"
        )


class TestRSSFeedMonitorSourceDetection:
    """Tests that RSS feed monitor correctly detects source from URL.

    Note: These tests require proper environment setup (OpenAI API key, etc.)
    and are skipped if imports fail.
    """

    @pytest.mark.skipif(
        True,
        reason="Import requires OpenAI client setup - run manually with env vars",
    )
    def test_determine_feed_source_for_inail(self):
        """Verify INAIL URLs are correctly identified."""
        from app.ingest.rss_normativa import _determine_feed_source

        source, source_type = _determine_feed_source(
            "https://www.inail.it/portale/it.rss.news.xml"
        )

        assert source == "inail", f"Expected 'inail', got '{source}'"

    @pytest.mark.skipif(
        True,
        reason="Import requires OpenAI client setup - run manually with env vars",
    )
    def test_determine_feed_source_for_agenzia_entrate(self):
        """Verify Agenzia Entrate URLs are correctly identified."""
        from app.ingest.rss_normativa import _determine_feed_source

        source, source_type = _determine_feed_source(
            "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=abc"
        )

        assert source == "agenzia_entrate", f"Expected 'agenzia_entrate', got '{source}'"
