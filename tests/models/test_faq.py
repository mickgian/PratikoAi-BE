"""Tests for FAQ system models."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.faq import (
    FAQAnalyticsSummary,
    FAQCategory,
    FAQEntry,
    FAQObsolescenceCheck,
    FAQUsageLog,
    FAQVariationCache,
    FAQVersionHistory,
    UpdateSensitivity,
    calculate_cost_savings,
    generate_faq_cache_key,
    get_faq_search_vector,
)


class TestUpdateSensitivity:
    """Test UpdateSensitivity enum."""

    def test_update_sensitivity_values(self):
        """Test that update sensitivity levels have correct values."""
        assert UpdateSensitivity.LOW.value == "low"
        assert UpdateSensitivity.MEDIUM.value == "medium"
        assert UpdateSensitivity.HIGH.value == "high"

    def test_update_sensitivity_enum_members(self):
        """Test that all expected sensitivity levels exist."""
        expected = {"LOW", "MEDIUM", "HIGH"}
        actual = {member.name for member in UpdateSensitivity}
        assert actual == expected


class TestFAQEntry:
    """Test FAQEntry model."""

    def test_create_faq_entry_minimal(self):
        """Test creating FAQ entry with required fields."""
        entry = FAQEntry(
            question="Cos'è un CCNL?",
            answer="Un CCNL è un Contratto Collettivo Nazionale di Lavoro.",
        )

        assert entry.question == "Cos'è un CCNL?"
        assert entry.answer == "Un CCNL è un Contratto Collettivo Nazionale di Lavoro."
        assert entry.category == "generale"
        assert entry.tags == []
        assert entry.language == "it"
        assert entry.needs_review is False
        assert entry.update_sensitivity == UpdateSensitivity.MEDIUM
        assert entry.hit_count == 0
        assert entry.last_used is None
        assert entry.avg_helpfulness is None
        assert entry.version == 1
        assert entry.previous_version_id is None

    def test_create_faq_entry_with_category(self):
        """Test creating FAQ entry with category and tags."""
        entry = FAQEntry(
            question="Come si calcolano le detrazioni fiscali?",
            answer="Le detrazioni fiscali si calcolano...",
            category="tasse",
            tags=["detrazioni", "fiscale", "2025"],
            language="it",
        )

        assert entry.category == "tasse"
        assert "detrazioni" in entry.tags
        assert "fiscale" in entry.tags
        assert len(entry.tags) == 3

    def test_faq_entry_with_regulatory_refs(self):
        """Test FAQ entry with regulatory references."""
        refs = {
            "law": "DPR 917/1986",
            "article": "15",
            "updated": "2025-01-01",
        }

        entry = FAQEntry(
            question="Qual è la normativa di riferimento?",
            answer="La normativa di riferimento è...",
            regulatory_refs=refs,
        )

        assert entry.regulatory_refs == refs
        assert entry.regulatory_refs["law"] == "DPR 917/1986"

    def test_faq_entry_with_update_sensitivity(self):
        """Test FAQ entry with different sensitivity levels."""
        high_sensitivity = FAQEntry(
            question="Aliquote IRPEF 2025",
            answer="Le aliquote IRPEF per il 2025 sono...",
            update_sensitivity=UpdateSensitivity.HIGH,
        )

        low_sensitivity = FAQEntry(
            question="Storia del sistema fiscale italiano",
            answer="Il sistema fiscale italiano ha una lunga storia...",
            update_sensitivity=UpdateSensitivity.LOW,
        )

        assert high_sensitivity.update_sensitivity == UpdateSensitivity.HIGH
        assert low_sensitivity.update_sensitivity == UpdateSensitivity.LOW

    def test_faq_entry_with_usage_stats(self):
        """Test FAQ entry with usage statistics."""
        last_used = datetime.now(UTC)

        entry = FAQEntry(
            question="Test FAQ",
            answer="Test answer",
            hit_count=150,
            last_used=last_used,
            avg_helpfulness=0.87,
        )

        assert entry.hit_count == 150
        assert entry.last_used == last_used
        assert entry.avg_helpfulness == 0.87

    def test_faq_entry_with_version_tracking(self):
        """Test FAQ entry with version tracking."""
        entry = FAQEntry(
            question="Updated FAQ",
            answer="Updated answer",
            version=3,
            previous_version_id="prev-uuid-123",
        )

        assert entry.version == 3
        assert entry.previous_version_id == "prev-uuid-123"

    def test_faq_entry_needs_review(self):
        """Test FAQ entry flagged for review."""
        entry = FAQEntry(
            question="FAQ che necessita revisione",
            answer="Questa risposta potrebbe essere obsoleta",
            needs_review=True,
        )

        assert entry.needs_review is True

    def test_faq_entry_timestamps_auto_created(self):
        """Test that timestamps are automatically created."""
        entry = FAQEntry(
            question="Test timestamp",
            answer="Test answer",
        )

        assert entry.created_at is not None
        assert entry.updated_at is not None
        assert isinstance(entry.created_at, datetime)


class TestFAQUsageLog:
    """Test FAQUsageLog model."""

    def test_create_usage_log_minimal(self):
        """Test creating usage log with required fields."""
        log = FAQUsageLog(
            faq_id="faq-123",
            response_variation="Risposta variata per l'utente",
        )

        assert log.faq_id == "faq-123"
        assert log.response_variation == "Risposta variata per l'utente"
        assert log.user_id is None
        assert log.from_cache is False
        assert log.variation_cost_euros == 0.0003
        assert log.variation_cost_cents == 3
        assert log.was_helpful is None
        assert log.followup_needed is None
        assert log.comments is None

    def test_usage_log_with_user(self):
        """Test usage log with user information."""
        log = FAQUsageLog(
            faq_id="faq-123",
            user_id="user-456",
            response_variation="Variazione personalizzata",
        )

        assert log.user_id == "user-456"

    def test_usage_log_from_cache(self):
        """Test usage log for cached response."""
        log = FAQUsageLog(
            faq_id="faq-123",
            response_variation="Cached response",
            from_cache=True,
            variation_cost_euros=0.0,
            variation_cost_cents=0,
        )

        assert log.from_cache is True
        assert log.variation_cost_euros == 0.0
        assert log.variation_cost_cents == 0

    def test_usage_log_with_feedback(self):
        """Test usage log with user feedback."""
        feedback_time = datetime.now(UTC)

        log = FAQUsageLog(
            faq_id="faq-123",
            response_variation="Risposta utile",
            was_helpful=True,
            followup_needed=False,
            comments="Risposta molto chiara, grazie!",
            feedback_submitted_at=feedback_time,
        )

        assert log.was_helpful is True
        assert log.followup_needed is False
        assert log.comments is not None
        assert "chiara" in log.comments
        assert log.feedback_submitted_at == feedback_time

    def test_usage_log_negative_feedback(self):
        """Test usage log with negative feedback."""
        log = FAQUsageLog(
            faq_id="faq-123",
            response_variation="Risposta non sufficiente",
            was_helpful=False,
            followup_needed=True,
            comments="Vorrei più dettagli",
        )

        assert log.was_helpful is False
        assert log.followup_needed is True

    def test_usage_log_timestamp_auto_created(self):
        """Test that timestamp is automatically created."""
        log = FAQUsageLog(
            faq_id="faq-123",
            response_variation="Test",
        )

        assert log.used_at is not None
        assert isinstance(log.used_at, datetime)


class TestFAQVersionHistory:
    """Test FAQVersionHistory model."""

    def test_create_version_history_minimal(self):
        """Test creating version history with required fields."""
        version = FAQVersionHistory(
            faq_id="faq-123",
            version=2,
            question="Domanda versione 2",
            answer="Risposta versione 2",
        )

        assert version.faq_id == "faq-123"
        assert version.version == 2
        assert version.question == "Domanda versione 2"
        assert version.answer == "Risposta versione 2"
        assert version.tags == []
        assert version.change_reason is None
        assert version.changed_by is None

    def test_version_history_with_tags(self):
        """Test version history with tags."""
        version = FAQVersionHistory(
            faq_id="faq-123",
            version=3,
            question="Test",
            answer="Test",
            tags=["tag1", "tag2", "updated"],
        )

        assert len(version.tags) == 3
        assert "updated" in version.tags

    def test_version_history_with_change_tracking(self):
        """Test version history with change tracking."""
        version = FAQVersionHistory(
            faq_id="faq-123",
            version=4,
            question="Updated question",
            answer="Updated answer",
            change_reason="Aggiornamento normativo DL 5/2025",
            changed_by="admin@example.com",
        )

        assert version.change_reason is not None
        assert "normativo" in version.change_reason
        assert version.changed_by == "admin@example.com"

    def test_version_history_with_regulatory_refs(self):
        """Test version history with regulatory references."""
        refs = {"decree": "DL 5/2025", "effective_date": "2025-02-01"}

        version = FAQVersionHistory(
            faq_id="faq-123",
            version=5,
            question="FAQ aggiornata",
            answer="Risposta aggiornata",
            regulatory_refs=refs,
        )

        assert version.regulatory_refs["decree"] == "DL 5/2025"

    def test_version_history_timestamp_auto_created(self):
        """Test that timestamp is automatically created."""
        version = FAQVersionHistory(
            faq_id="faq-123",
            version=1,
            question="Test",
            answer="Test",
        )

        assert version.created_at is not None


class TestFAQObsolescenceCheck:
    """Test FAQObsolescenceCheck model."""

    def test_create_obsolescence_check_minimal(self):
        """Test creating obsolescence check with required fields."""
        check = FAQObsolescenceCheck(
            faq_id="faq-123",
        )

        assert check.faq_id == "faq-123"
        assert check.is_potentially_obsolete is False
        assert check.confidence_score == 0.0
        assert check.reason is None
        assert check.action_taken is None
        assert check.reviewed_by is None
        assert check.reviewed_at is None

    def test_obsolescence_check_not_obsolete(self):
        """Test obsolescence check with no issues."""
        check = FAQObsolescenceCheck(
            faq_id="faq-123",
            is_potentially_obsolete=False,
            confidence_score=0.95,
        )

        assert check.is_potentially_obsolete is False
        assert check.confidence_score == 0.95

    def test_obsolescence_check_potentially_obsolete(self):
        """Test obsolescence check flagging potential obsolescence."""
        updates = {
            "update_id": "update-789",
            "title": "Nuovo decreto fiscale 2025",
            "affects": ["detrazioni", "aliquote"],
        }

        check = FAQObsolescenceCheck(
            faq_id="faq-123",
            is_potentially_obsolete=True,
            confidence_score=0.78,
            reason="FAQ menziona aliquote IRPEF che potrebbero essere cambiate dal DL 5/2025",
            affecting_updates=updates,
        )

        assert check.is_potentially_obsolete is True
        assert check.confidence_score == 0.78
        assert "aliquote" in check.reason
        assert check.affecting_updates["update_id"] == "update-789"

    def test_obsolescence_check_with_action(self):
        """Test obsolescence check with action taken."""
        check = FAQObsolescenceCheck(
            faq_id="faq-123",
            is_potentially_obsolete=True,
            confidence_score=0.85,
            action_taken="review_flagged",
        )

        assert check.action_taken == "review_flagged"

    def test_obsolescence_check_reviewed(self):
        """Test obsolescence check after review."""
        reviewed_time = datetime.now(UTC)

        check = FAQObsolescenceCheck(
            faq_id="faq-123",
            is_potentially_obsolete=True,
            confidence_score=0.80,
            action_taken="auto_updated",
            reviewed_by="admin@example.com",
            reviewed_at=reviewed_time,
        )

        assert check.reviewed_by == "admin@example.com"
        assert check.reviewed_at == reviewed_time

    def test_obsolescence_check_timestamp_auto_created(self):
        """Test that timestamp is automatically created."""
        check = FAQObsolescenceCheck(faq_id="faq-123")

        assert check.checked_at is not None


class TestFAQCategory:
    """Test FAQCategory model."""

    def test_create_category_minimal(self):
        """Test creating category with required fields."""
        category = FAQCategory(
            name="tasse",
            display_name="Tasse e Imposte",
        )

        assert category.name == "tasse"
        assert category.display_name == "Tasse e Imposte"
        assert category.description is None
        assert category.parent_category is None
        assert category.sort_order == 0
        assert category.faq_count == 0
        assert category.total_hits == 0
        assert category.avg_helpfulness is None
        assert category.is_active is True

    def test_create_category_with_description(self):
        """Test creating category with description."""
        category = FAQCategory(
            name="ccnl",
            display_name="CCNL e Contratti",
            description="Domande sui Contratti Collettivi Nazionali di Lavoro",
        )

        assert category.description is not None
        assert "Contratti Collettivi" in category.description

    def test_create_category_with_hierarchy(self):
        """Test creating category with parent."""
        category = FAQCategory(
            name="detrazioni_lavoro",
            display_name="Detrazioni Lavoro Dipendente",
            parent_category="tasse",
            sort_order=1,
        )

        assert category.parent_category == "tasse"
        assert category.sort_order == 1

    def test_category_with_statistics(self):
        """Test category with usage statistics."""
        category = FAQCategory(
            name="generale",
            display_name="Domande Generali",
            faq_count=25,
            total_hits=1500,
            avg_helpfulness=0.82,
        )

        assert category.faq_count == 25
        assert category.total_hits == 1500
        assert category.avg_helpfulness == 0.82

    def test_category_inactive(self):
        """Test inactive category."""
        category = FAQCategory(
            name="obsolete",
            display_name="Categoria Obsoleta",
            is_active=False,
        )

        assert category.is_active is False

    def test_category_timestamps_auto_created(self):
        """Test that timestamps are automatically created."""
        category = FAQCategory(
            name="test",
            display_name="Test Category",
        )

        assert category.created_at is not None
        assert category.updated_at is not None


class TestFAQVariationCache:
    """Test FAQVariationCache model."""

    def test_create_variation_cache_minimal(self):
        """Test creating variation cache with required fields."""
        cache = FAQVariationCache(
            faq_id="faq-123",
            cache_key="faq_var:abc123def456",
            original_answer="Risposta originale",
            variation_text="Risposta variata",
        )

        assert cache.faq_id == "faq-123"
        assert cache.cache_key == "faq_var:abc123def456"
        assert cache.original_answer == "Risposta originale"
        assert cache.variation_text == "Risposta variata"
        assert cache.user_id is None
        assert cache.model_used == "gpt-3.5-turbo"
        assert cache.tokens_used is None
        assert cache.generation_cost_euros == 0.0003
        assert cache.hit_count == 0
        assert cache.last_used is None

    def test_variation_cache_with_user(self):
        """Test variation cache for specific user."""
        cache = FAQVariationCache(
            faq_id="faq-123",
            user_id="user-456",
            cache_key="faq_var:user456abc",
            original_answer="Original",
            variation_text="Variation",
        )

        assert cache.user_id == "user-456"

    def test_variation_cache_with_generation_details(self):
        """Test variation cache with generation metadata."""
        cache = FAQVariationCache(
            faq_id="faq-123",
            cache_key="faq_var:xyz789",
            original_answer="Original",
            variation_text="Variation",
            model_used="gpt-4",
            tokens_used=250,
            generation_cost_euros=0.001,
        )

        assert cache.model_used == "gpt-4"
        assert cache.tokens_used == 250
        assert cache.generation_cost_euros == 0.001

    def test_variation_cache_with_usage(self):
        """Test variation cache with usage tracking."""
        last_used = datetime.now(UTC)

        cache = FAQVariationCache(
            faq_id="faq-123",
            cache_key="faq_var:used123",
            original_answer="Original",
            variation_text="Variation",
            hit_count=15,
            last_used=last_used,
        )

        assert cache.hit_count == 15
        assert cache.last_used == last_used

    def test_variation_cache_timestamps_auto_created(self):
        """Test that timestamps are automatically created."""
        cache = FAQVariationCache(
            faq_id="faq-123",
            cache_key="faq_var:ts123",
            original_answer="Original",
            variation_text="Variation",
        )

        assert cache.created_at is not None
        assert cache.expires_at is not None


class TestFAQAnalyticsSummary:
    """Test FAQAnalyticsSummary model."""

    def test_create_analytics_summary_minimal(self):
        """Test creating analytics summary with required fields."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(hours=24)

        summary = FAQAnalyticsSummary(
            period_start=period_start,
            period_end=period_end,
            period_type="daily",
        )

        assert summary.period_start == period_start
        assert summary.period_end == period_end
        assert summary.period_type == "daily"
        assert summary.total_queries == 0
        assert summary.faq_responses == 0
        assert summary.full_llm_responses == 0
        assert summary.cache_hits == 0
        assert summary.cache_misses == 0
        assert summary.avg_response_time_ms == 0.0
        assert summary.total_variation_costs_euros == 0.0
        assert summary.cost_savings_euros == 0.0

    def test_analytics_summary_daily(self):
        """Test daily analytics summary."""
        period_start = datetime.now(UTC).replace(hour=0, minute=0, second=0)
        period_end = period_start + timedelta(days=1)

        summary = FAQAnalyticsSummary(
            period_start=period_start,
            period_end=period_end,
            period_type="daily",
            total_queries=1000,
            faq_responses=700,
            full_llm_responses=300,
            cache_hits=450,
            cache_misses=250,
        )

        assert summary.total_queries == 1000
        assert summary.faq_responses == 700
        assert summary.full_llm_responses == 300

    def test_analytics_summary_with_performance_metrics(self):
        """Test analytics summary with performance metrics."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(hours=1)

        summary = FAQAnalyticsSummary(
            period_start=period_start,
            period_end=period_end,
            period_type="hourly",
            avg_response_time_ms=125.5,
            avg_search_time_ms=45.2,
            cache_hit_rate=0.64,
        )

        assert summary.avg_response_time_ms == 125.5
        assert summary.avg_search_time_ms == 45.2
        assert summary.cache_hit_rate == 0.64

    def test_analytics_summary_with_cost_metrics(self):
        """Test analytics summary with cost metrics."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=7)

        summary = FAQAnalyticsSummary(
            period_start=period_start,
            period_end=period_end,
            period_type="weekly",
            total_queries=5000,
            faq_responses=3500,
            total_variation_costs_euros=0.35,
            total_full_llm_costs_euros=3.00,
            cost_savings_euros=6.65,
            cost_savings_percent=68.9,
        )

        assert summary.total_variation_costs_euros == 0.35
        assert summary.total_full_llm_costs_euros == 3.00
        assert summary.cost_savings_euros == 6.65
        assert summary.cost_savings_percent == 68.9

    def test_analytics_summary_with_quality_metrics(self):
        """Test analytics summary with quality metrics."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=30)

        summary = FAQAnalyticsSummary(
            period_start=period_start,
            period_end=period_end,
            period_type="monthly",
            avg_helpfulness_score=0.85,
            followup_rate=0.12,
            obsolescence_flags=5,
        )

        assert summary.avg_helpfulness_score == 0.85
        assert summary.followup_rate == 0.12
        assert summary.obsolescence_flags == 5

    def test_analytics_summary_with_popular_content(self):
        """Test analytics summary with popular content tracking."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=7)

        top_categories = [
            {"name": "tasse", "hits": 1500},
            {"name": "ccnl", "hits": 1200},
        ]

        top_faqs = [
            {"id": "faq-123", "question": "Cos'è un CCNL?", "hits": 450},
            {"id": "faq-456", "question": "Come calcolare IRPEF?", "hits": 380},
        ]

        summary = FAQAnalyticsSummary(
            period_start=period_start,
            period_end=period_end,
            period_type="weekly",
            top_categories=top_categories,
            top_faqs=top_faqs,
        )

        assert len(summary.top_categories) == 2
        assert summary.top_categories[0]["name"] == "tasse"
        assert len(summary.top_faqs) == 2
        assert summary.top_faqs[0]["hits"] == 450

    def test_analytics_summary_timestamp_auto_created(self):
        """Test that timestamp is automatically created."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=1)

        summary = FAQAnalyticsSummary(
            period_start=period_start,
            period_end=period_end,
            period_type="daily",
        )

        assert summary.created_at is not None


class TestHelperFunctions:
    """Test helper functions."""

    def test_generate_faq_cache_key(self):
        """Test cache key generation."""
        key = generate_faq_cache_key("faq-123", "user-456")

        assert key.startswith("faq_var:")
        assert len(key) > len("faq_var:")

    def test_generate_faq_cache_key_with_context(self):
        """Test cache key generation with context."""
        key1 = generate_faq_cache_key("faq-123", "user-456", "context1")
        key2 = generate_faq_cache_key("faq-123", "user-456", "context2")

        assert key1 != key2  # Different contexts should produce different keys

    def test_generate_faq_cache_key_deterministic(self):
        """Test that cache key generation is deterministic."""
        key1 = generate_faq_cache_key("faq-123", "user-456")
        key2 = generate_faq_cache_key("faq-123", "user-456")

        assert key1 == key2  # Same inputs should produce same key

    def test_calculate_cost_savings_basic(self):
        """Test basic cost savings calculation."""
        result = calculate_cost_savings(
            total_queries=1000,
            faq_responses=700,
        )

        assert "actual_costs_euros" in result
        assert "hypothetical_costs_euros" in result
        assert "savings_euros" in result
        assert "savings_percent" in result
        assert result["hypothetical_costs_euros"] == 1000 * 0.002  # 2.0
        assert result["savings_euros"] > 0
        assert result["savings_percent"] > 0

    def test_calculate_cost_savings_all_faq(self):
        """Test cost savings when all queries are FAQ responses."""
        result = calculate_cost_savings(
            total_queries=1000,
            faq_responses=1000,
        )

        assert result["full_llm_costs_euros"] == 0.0  # No full LLM responses
        assert result["variation_costs_euros"] > 0  # 30% of FAQs need variations
        assert result["savings_euros"] > 0

    def test_calculate_cost_savings_no_faq(self):
        """Test cost savings when no FAQ responses."""
        result = calculate_cost_savings(
            total_queries=1000,
            faq_responses=0,
        )

        assert result["full_llm_costs_euros"] == 1000 * 0.002  # All queries use full LLM
        assert result["variation_costs_euros"] == 0.0  # No variations needed
        assert result["savings_euros"] == 0.0
        assert result["savings_percent"] == 0.0

    def test_calculate_cost_savings_custom_costs(self):
        """Test cost savings with custom cost parameters."""
        result = calculate_cost_savings(
            total_queries=1000,
            faq_responses=500,
            variation_cost_per_query=0.0005,
            full_llm_cost_per_query=0.003,
        )

        assert result["variation_costs_euros"] == 500 * 0.30 * 0.0005  # 30% need variations
        assert result["full_llm_costs_euros"] == 500 * 0.003

    def test_calculate_cost_savings_zero_queries(self):
        """Test cost savings with zero queries."""
        result = calculate_cost_savings(
            total_queries=0,
            faq_responses=0,
        )

        assert result["savings_percent"] == 0.0
        assert result["actual_costs_euros"] == 0.0
        assert result["hypothetical_costs_euros"] == 0.0

    def test_get_faq_search_vector(self):
        """Test search vector generation."""
        vector = get_faq_search_vector(
            question="Cos'è un CCNL?",
            answer="Un CCNL è un Contratto Collettivo Nazionale di Lavoro",
            tags=["ccnl", "contratto"],
        )

        assert "ccnl" in vector
        assert "contratto" in vector
        assert vector == vector.lower()  # Should be lowercase

    def test_get_faq_search_vector_empty_tags(self):
        """Test search vector generation with empty tags."""
        vector = get_faq_search_vector(
            question="Test question",
            answer="Test answer",
            tags=[],
        )

        assert "test" in vector
        assert "question" in vector
        assert "answer" in vector

    def test_get_faq_search_vector_multiple_tags(self):
        """Test search vector generation with multiple tags."""
        vector = get_faq_search_vector(
            question="Question",
            answer="Answer",
            tags=["tag1", "tag2", "tag3"],
        )

        assert "tag1" in vector
        assert "tag2" in vector
        assert "tag3" in vector
