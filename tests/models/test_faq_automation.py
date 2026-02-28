"""Tests for FAQ Automation models.

Validates enums, SQLModel pure methods, helper functions, and configuration
for the automated FAQ generation system. All model tests instantiate
objects in memory without requiring a database connection.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.faq_automation import (
    FAQ_AUTOMATION_CONFIG,
    FAQApprovalStatus,
    FAQCandidate,
    FAQGenerationJob,
    FAQGenerationStatus,
    GeneratedFAQ,
    QueryCluster,
    RSSFAQImpact,
    RSSImpactLevel,
    calculate_faq_priority,
    estimate_generation_cost,
)

# ──────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────


class TestFAQGenerationStatus:
    """Tests for FAQGenerationStatus enum."""

    def test_all_values_exist(self):
        assert FAQGenerationStatus.PENDING.value == "pending"
        assert FAQGenerationStatus.PROCESSING.value == "processing"
        assert FAQGenerationStatus.COMPLETED.value == "completed"
        assert FAQGenerationStatus.FAILED.value == "failed"
        assert FAQGenerationStatus.CANCELLED.value == "cancelled"

    def test_count(self):
        assert len(FAQGenerationStatus) == 5


class TestFAQApprovalStatus:
    """Tests for FAQApprovalStatus enum."""

    def test_all_values_exist(self):
        assert FAQApprovalStatus.PENDING_REVIEW.value == "pending_review"
        assert FAQApprovalStatus.AUTO_APPROVED.value == "auto_approved"
        assert FAQApprovalStatus.MANUALLY_APPROVED.value == "manually_approved"
        assert FAQApprovalStatus.REJECTED.value == "rejected"
        assert FAQApprovalStatus.NEEDS_REVISION.value == "needs_revision"

    def test_count(self):
        assert len(FAQApprovalStatus) == 5


class TestRSSImpactLevel:
    """Tests for RSSImpactLevel enum."""

    def test_all_values_exist(self):
        assert RSSImpactLevel.LOW.value == "low"
        assert RSSImpactLevel.MEDIUM.value == "medium"
        assert RSSImpactLevel.HIGH.value == "high"
        assert RSSImpactLevel.CRITICAL.value == "critical"

    def test_count(self):
        assert len(RSSImpactLevel) == 4


# ──────────────────────────────────────────────────────────────
# QueryCluster model
# ──────────────────────────────────────────────────────────────


class TestQueryClusterCalculateMonthlySavings:
    """Tests for QueryCluster.calculate_monthly_savings()."""

    def _make_cluster(self, **overrides):
        """Create a QueryCluster instance with sensible defaults."""
        now = datetime.utcnow()
        defaults = {
            "canonical_query": "What is IRPEF?",
            "normalized_form": "what is irpef",
            "query_count": 100,
            "first_seen": now - timedelta(days=30),
            "last_seen": now,
            "total_cost_cents": 500,
            "avg_cost_cents": 5,
            "potential_savings_cents": 0,
            "avg_quality_score": Decimal("0.85"),
            "avg_response_time_ms": 200,
            "query_variations": [],
            "semantic_tags": [],
            "roi_score": Decimal("10.0"),
            "priority_score": Decimal("5.0"),
            "processing_status": "discovered",
            "last_analyzed": now,
            "created_at": now,
        }
        defaults.update(overrides)
        return QueryCluster(**defaults)

    def test_savings_positive_with_queries(self):
        cluster = self._make_cluster(query_count=100, avg_cost_cents=5)
        savings = cluster.calculate_monthly_savings(days_window=30)
        assert savings > Decimal("0")

    def test_savings_zero_when_no_queries(self):
        cluster = self._make_cluster(query_count=0, avg_cost_cents=5)
        savings = cluster.calculate_monthly_savings(days_window=30)
        assert savings == Decimal("0")

    def test_savings_zero_when_zero_window(self):
        cluster = self._make_cluster(query_count=100, avg_cost_cents=5)
        savings = cluster.calculate_monthly_savings(days_window=0)
        assert savings == Decimal("0")

    def test_savings_scales_with_query_count(self):
        cluster_low = self._make_cluster(query_count=10, avg_cost_cents=10)
        cluster_high = self._make_cluster(query_count=1000, avg_cost_cents=10)
        savings_low = cluster_low.calculate_monthly_savings(days_window=30)
        savings_high = cluster_high.calculate_monthly_savings(days_window=30)
        assert savings_high > savings_low

    def test_savings_scales_with_window(self):
        cluster = self._make_cluster(query_count=100, avg_cost_cents=10)
        savings_short = cluster.calculate_monthly_savings(days_window=7)
        savings_long = cluster.calculate_monthly_savings(days_window=30)
        # Shorter window extrapolates higher monthly rate
        assert savings_short > savings_long

    def test_savings_never_negative(self):
        cluster = self._make_cluster(query_count=1, avg_cost_cents=0)
        savings = cluster.calculate_monthly_savings(days_window=30)
        assert savings >= Decimal("0")


class TestQueryClusterUpdateStatistics:
    """Tests for QueryCluster.update_statistics()."""

    def _make_cluster(self, **overrides):
        now = datetime.utcnow()
        defaults = {
            "canonical_query": "test",
            "normalized_form": "test",
            "query_count": 10,
            "first_seen": now - timedelta(days=30),
            "last_seen": now - timedelta(days=1),
            "total_cost_cents": 50,
            "avg_cost_cents": 5,
            "potential_savings_cents": 0,
            "avg_quality_score": Decimal("0.80"),
            "avg_response_time_ms": 100,
            "query_variations": [],
            "semantic_tags": [],
            "roi_score": Decimal("1.0"),
            "priority_score": Decimal("1.0"),
            "processing_status": "discovered",
            "last_analyzed": now,
            "created_at": now,
        }
        defaults.update(overrides)
        return QueryCluster(**defaults)

    def test_empty_queries_no_change(self):
        cluster = self._make_cluster()
        original_count = cluster.query_count
        cluster.update_statistics([])
        assert cluster.query_count == original_count

    def test_query_count_incremented(self):
        cluster = self._make_cluster(query_count=10)
        new_queries = [
            {"cost_cents": 3, "quality_score": 0.9},
            {"cost_cents": 4, "quality_score": 0.85},
        ]
        cluster.update_statistics(new_queries)
        assert cluster.query_count == 12

    def test_total_cost_updated(self):
        cluster = self._make_cluster(total_cost_cents=50)
        new_queries = [{"cost_cents": 10}, {"cost_cents": 20}]
        cluster.update_statistics(new_queries)
        assert cluster.total_cost_cents == 80

    def test_avg_cost_recalculated(self):
        cluster = self._make_cluster(query_count=10, total_cost_cents=50)
        new_queries = [{"cost_cents": 10}, {"cost_cents": 10}]
        cluster.update_statistics(new_queries)
        # total_cost_cents = 50 + 20 = 70, query_count = 12
        assert cluster.avg_cost_cents == 70 // 12

    def test_last_seen_updated_with_timestamps(self):
        now = datetime.utcnow()
        future = now + timedelta(hours=1)
        cluster = self._make_cluster(last_seen=now)
        new_queries = [{"cost_cents": 5, "timestamp": future}]
        cluster.update_statistics(new_queries)
        assert cluster.last_seen == future

    def test_quality_scores_updated(self):
        cluster = self._make_cluster(query_count=2, avg_quality_score=Decimal("0.80"))
        new_queries = [{"cost_cents": 5, "quality_score": 1.0}]
        cluster.update_statistics(new_queries)
        # Quality is recalculated as weighted average
        assert float(cluster.avg_quality_score) > 0.0


class TestQueryClusterToDict:
    """Tests for QueryCluster.to_dict()."""

    def test_returns_expected_keys(self):
        now = datetime.utcnow()
        cluster = QueryCluster(
            canonical_query="test query",
            normalized_form="test query",
            query_count=5,
            first_seen=now,
            last_seen=now,
            total_cost_cents=25,
            avg_cost_cents=5,
            potential_savings_cents=10,
            avg_quality_score=Decimal("0.90"),
            avg_response_time_ms=150,
            query_variations=["test", "testing"],
            semantic_tags=["tax"],
            roi_score=Decimal("2.5"),
            priority_score=Decimal("3.0"),
            processing_status="discovered",
            last_analyzed=now,
            created_at=now,
        )
        result = cluster.to_dict()
        expected_keys = {
            "id",
            "canonical_query",
            "normalized_form",
            "query_count",
            "query_variations",
            "semantic_tags",
            "avg_cost_cents",
            "potential_savings_cents",
            "avg_quality_score",
            "roi_score",
            "priority_score",
            "processing_status",
            "first_seen",
            "last_seen",
        }
        assert set(result.keys()) == expected_keys

    def test_query_variations_limited_to_10(self):
        now = datetime.utcnow()
        cluster = QueryCluster(
            canonical_query="test",
            normalized_form="test",
            query_count=1,
            first_seen=now,
            last_seen=now,
            avg_quality_score=Decimal("0.80"),
            roi_score=Decimal("1.0"),
            priority_score=Decimal("1.0"),
            processing_status="discovered",
            last_analyzed=now,
            created_at=now,
            query_variations=[f"variation_{i}" for i in range(20)],
            semantic_tags=[],
        )
        result = cluster.to_dict()
        assert len(result["query_variations"]) == 10


# ──────────────────────────────────────────────────────────────
# FAQCandidate model
# ──────────────────────────────────────────────────────────────


class TestFAQCandidateCanGenerate:
    """Tests for FAQCandidate.can_generate()."""

    def _make_candidate(self, **overrides):
        now = datetime.utcnow()
        defaults = {
            "cluster_id": uuid4(),
            "suggested_question": "What is IRPEF?",
            "best_response_content": "IRPEF is the personal income tax in Italy.",
            "frequency": 50,
            "status": "pending",
            "generation_attempts": 0,
            "max_generation_attempts": 3,
            "expires_at": None,
            "created_at": now,
            "suggested_tags": [],
            "regulatory_references": [],
        }
        defaults.update(overrides)
        return FAQCandidate(**defaults)

    def test_can_generate_when_pending(self):
        candidate = self._make_candidate()
        assert candidate.can_generate() is True

    def test_cannot_generate_when_not_pending(self):
        candidate = self._make_candidate(status="completed")
        assert candidate.can_generate() is False

    def test_cannot_generate_when_max_attempts_reached(self):
        candidate = self._make_candidate(generation_attempts=3, max_generation_attempts=3)
        assert candidate.can_generate() is False

    def test_cannot_generate_when_expired(self):
        expired = datetime.utcnow() - timedelta(hours=1)
        candidate = self._make_candidate(expires_at=expired)
        assert candidate.can_generate() is False

    def test_can_generate_when_not_yet_expired(self):
        future = datetime.utcnow() + timedelta(days=7)
        candidate = self._make_candidate(expires_at=future)
        assert candidate.can_generate() is True

    def test_cannot_generate_failed_status(self):
        candidate = self._make_candidate(status="failed")
        assert candidate.can_generate() is False


class TestFAQCandidateCalculatePriority:
    """Tests for FAQCandidate.calculate_priority()."""

    def _make_candidate(self, **overrides):
        now = datetime.utcnow()
        defaults = {
            "cluster_id": uuid4(),
            "suggested_question": "test",
            "best_response_content": "test answer",
            "frequency": 100,
            "roi_score": Decimal("5.0"),
            "status": "pending",
            "created_at": now,
            "suggested_tags": [],
            "regulatory_references": [],
        }
        defaults.update(overrides)
        return FAQCandidate(**defaults)

    def test_priority_without_expiry(self):
        candidate = self._make_candidate(roi_score=Decimal("5.0"), frequency=100)
        priority = candidate.calculate_priority()
        # Without expiry, urgency_factor = 1.0
        # priority = 5.0 * 100 * 1.0 = 500.0
        assert priority == Decimal("500.0")

    def test_priority_with_near_expiry(self):
        near_future = datetime.utcnow() + timedelta(days=1)
        candidate = self._make_candidate(
            roi_score=Decimal("5.0"),
            frequency=100,
            expires_at=near_future,
        )
        priority = candidate.calculate_priority()
        # Near expiry increases urgency
        assert priority > Decimal("0")

    def test_priority_scales_with_frequency(self):
        low = self._make_candidate(frequency=10)
        high = self._make_candidate(frequency=1000)
        assert high.calculate_priority() > low.calculate_priority()

    def test_priority_scales_with_roi(self):
        low = self._make_candidate(roi_score=Decimal("1.0"))
        high = self._make_candidate(roi_score=Decimal("10.0"))
        assert high.calculate_priority() > low.calculate_priority()


class TestFAQCandidateToDict:
    """Tests for FAQCandidate.to_dict()."""

    def test_returns_expected_keys(self):
        now = datetime.utcnow()
        candidate = FAQCandidate(
            cluster_id=uuid4(),
            suggested_question="What is IRPEF?",
            best_response_content="IRPEF is...",
            frequency=50,
            status="pending",
            created_at=now,
            suggested_tags=["tax"],
            regulatory_references=["art. 1"],
        )
        result = candidate.to_dict()
        expected_keys = {
            "id",
            "cluster_id",
            "suggested_question",
            "suggested_category",
            "suggested_tags",
            "frequency",
            "estimated_monthly_savings",
            "roi_score",
            "priority_score",
            "status",
            "generation_attempts",
            "can_generate",
            "created_at",
            "expires_at",
        }
        assert set(result.keys()) == expected_keys

    def test_to_dict_can_generate_reflects_status(self):
        now = datetime.utcnow()
        candidate = FAQCandidate(
            cluster_id=uuid4(),
            suggested_question="test",
            best_response_content="answer",
            frequency=10,
            status="completed",
            created_at=now,
            suggested_tags=[],
            regulatory_references=[],
        )
        result = candidate.to_dict()
        assert result["can_generate"] is False


# ──────────────────────────────────────────────────────────────
# GeneratedFAQ model
# ──────────────────────────────────────────────────────────────


class TestGeneratedFAQShouldAutoApprove:
    """Tests for GeneratedFAQ.should_auto_approve()."""

    def _make_faq(self, **overrides):
        now = datetime.utcnow()
        defaults = {
            "candidate_id": uuid4(),
            "question": "What is IRPEF?",
            "answer": "IRPEF is the personal income tax.",
            "quality_score": Decimal("0.95"),
            "generation_model": "gpt-3.5-turbo",
            "source_query_count": 10,
            "legal_review_required": False,
            "estimated_monthly_savings": Decimal("5.0"),
            "created_at": now,
            "tags": [],
            "regulatory_refs": [],
        }
        defaults.update(overrides)
        return GeneratedFAQ(**defaults)

    def test_auto_approve_when_all_conditions_met(self):
        faq = self._make_faq()
        assert faq.should_auto_approve() is True

    def test_not_auto_approve_low_quality(self):
        faq = self._make_faq(quality_score=Decimal("0.90"))
        assert faq.should_auto_approve() is False

    def test_not_auto_approve_low_query_count(self):
        faq = self._make_faq(source_query_count=5)
        assert faq.should_auto_approve() is False

    def test_not_auto_approve_legal_review_required(self):
        faq = self._make_faq(legal_review_required=True)
        assert faq.should_auto_approve() is False

    def test_not_auto_approve_low_savings(self):
        faq = self._make_faq(estimated_monthly_savings=Decimal("4.0"))
        assert faq.should_auto_approve() is False


class TestGeneratedFAQCalculateImpactScore:
    """Tests for GeneratedFAQ.calculate_impact_score()."""

    def _make_faq(self, **overrides):
        now = datetime.utcnow()
        defaults = {
            "candidate_id": uuid4(),
            "question": "test",
            "answer": "answer",
            "quality_score": Decimal("0.90"),
            "generation_model": "gpt-3.5-turbo",
            "source_query_count": 10,
            "estimated_monthly_savings": Decimal("10.0"),
            "created_at": now,
            "tags": [],
            "regulatory_refs": [],
        }
        defaults.update(overrides)
        return GeneratedFAQ(**defaults)

    def test_impact_score_positive(self):
        faq = self._make_faq()
        score = faq.calculate_impact_score()
        assert score > Decimal("0")

    def test_impact_score_scales_with_quality(self):
        low = self._make_faq(quality_score=Decimal("0.50"))
        high = self._make_faq(quality_score=Decimal("0.99"))
        assert high.calculate_impact_score() > low.calculate_impact_score()

    def test_impact_score_caps_usage_factor(self):
        # source_query_count = 100 -> usage_factor = min(100/10, 2.0) = 2.0
        faq = self._make_faq(source_query_count=100)
        score = faq.calculate_impact_score()
        # Compare with source_query_count = 200 -> should be same (capped at 2.0)
        faq2 = self._make_faq(source_query_count=200)
        score2 = faq2.calculate_impact_score()
        assert score == score2

    def test_impact_score_caps_savings_factor(self):
        # savings = 30.0 -> savings_factor = min(30/10, 3.0) = 3.0
        faq = self._make_faq(estimated_monthly_savings=Decimal("30.0"))
        score = faq.calculate_impact_score()
        # savings = 50.0 -> savings_factor = min(50/10, 3.0) = 3.0 (capped)
        faq2 = self._make_faq(estimated_monthly_savings=Decimal("50.0"))
        score2 = faq2.calculate_impact_score()
        assert score == score2

    def test_impact_score_zero_quality_gives_zero(self):
        faq = self._make_faq(quality_score=Decimal("0.00"), source_query_count=0)
        score = faq.calculate_impact_score()
        assert score == Decimal("0")


class TestGeneratedFAQToDict:
    """Tests for GeneratedFAQ.to_dict()."""

    def test_returns_expected_keys(self):
        now = datetime.utcnow()
        faq = GeneratedFAQ(
            candidate_id=uuid4(),
            question="What is IRPEF?",
            answer="IRPEF is...",
            quality_score=Decimal("0.95"),
            generation_model="gpt-4",
            created_at=now,
            tags=["tax"],
            regulatory_refs=["art. 1"],
        )
        result = faq.to_dict()
        expected_keys = {
            "id",
            "candidate_id",
            "question",
            "answer",
            "category",
            "tags",
            "quality_score",
            "regulatory_refs",
            "generation_model",
            "generation_cost_cents",
            "estimated_monthly_savings",
            "approval_status",
            "published",
            "auto_generated",
            "view_count",
            "usage_count",
            "satisfaction_score",
            "created_at",
            "published_at",
        }
        assert set(result.keys()) == expected_keys

    def test_to_dict_satisfaction_score_none(self):
        now = datetime.utcnow()
        faq = GeneratedFAQ(
            candidate_id=uuid4(),
            question="test",
            answer="answer",
            quality_score=Decimal("0.90"),
            generation_model="gpt-3.5-turbo",
            created_at=now,
            tags=[],
            regulatory_refs=[],
        )
        result = faq.to_dict()
        assert result["satisfaction_score"] is None

    def test_to_dict_published_at_none(self):
        now = datetime.utcnow()
        faq = GeneratedFAQ(
            candidate_id=uuid4(),
            question="test",
            answer="answer",
            quality_score=Decimal("0.90"),
            generation_model="gpt-3.5-turbo",
            created_at=now,
            tags=[],
            regulatory_refs=[],
        )
        result = faq.to_dict()
        assert result["published_at"] is None

    def test_to_dict_with_published_at(self):
        now = datetime.utcnow()
        faq = GeneratedFAQ(
            candidate_id=uuid4(),
            question="test",
            answer="answer",
            quality_score=Decimal("0.90"),
            generation_model="gpt-3.5-turbo",
            created_at=now,
            published_at=now,
            tags=[],
            regulatory_refs=[],
        )
        result = faq.to_dict()
        assert result["published_at"] == now.isoformat()


# ──────────────────────────────────────────────────────────────
# RSSFAQImpact model
# ──────────────────────────────────────────────────────────────


class TestRSSFAQImpactRequiresImmediateAction:
    """Tests for RSSFAQImpact.requires_immediate_action()."""

    def _make_impact(self, **overrides):
        now = datetime.utcnow()
        defaults = {
            "faq_id": uuid4(),
            "rss_update_id": uuid4(),
            "impact_level": "high",
            "impact_score": Decimal("0.85"),
            "confidence_score": Decimal("0.90"),
            "rss_source": "gazzetta_ufficiale",
            "rss_title": "New tax regulation",
            "rss_published_date": now,
            "action_required": "review",
            "processed": False,
            "created_at": now,
            "matching_tags": [],
            "matching_keywords": [],
            "regulatory_changes": [],
        }
        defaults.update(overrides)
        return RSSFAQImpact(**defaults)

    def test_requires_action_high_impact(self):
        impact = self._make_impact(impact_level="high", confidence_score=Decimal("0.90"), processed=False)
        assert impact.requires_immediate_action() is True

    def test_requires_action_critical_impact(self):
        impact = self._make_impact(impact_level="critical", confidence_score=Decimal("0.85"), processed=False)
        assert impact.requires_immediate_action() is True

    def test_does_not_require_action_low_impact(self):
        impact = self._make_impact(impact_level="low")
        assert impact.requires_immediate_action() is False

    def test_does_not_require_action_medium_impact(self):
        impact = self._make_impact(impact_level="medium")
        assert impact.requires_immediate_action() is False

    def test_does_not_require_action_already_processed(self):
        impact = self._make_impact(impact_level="high", processed=True)
        assert impact.requires_immediate_action() is False

    def test_does_not_require_action_low_confidence(self):
        impact = self._make_impact(impact_level="high", confidence_score=Decimal("0.70"))
        assert impact.requires_immediate_action() is False


class TestRSSFAQImpactCalculateUrgencyScore:
    """Tests for RSSFAQImpact.calculate_urgency_score()."""

    def _make_impact(self, **overrides):
        now = datetime.utcnow()
        defaults = {
            "faq_id": uuid4(),
            "rss_update_id": uuid4(),
            "impact_level": "high",
            "impact_score": Decimal("0.85"),
            "confidence_score": Decimal("0.90"),
            "rss_source": "gazzetta_ufficiale",
            "rss_title": "New regulation",
            "rss_published_date": now,
            "action_required": "review",
            "processed": False,
            "created_at": now,
            "matching_tags": [],
            "matching_keywords": [],
            "regulatory_changes": [],
        }
        defaults.update(overrides)
        return RSSFAQImpact(**defaults)

    def test_urgency_positive_for_recent_critical(self):
        impact = self._make_impact(impact_level="critical", confidence_score=Decimal("0.95"))
        score = impact.calculate_urgency_score()
        assert score > Decimal("0")

    def test_urgency_higher_for_critical_than_low(self):
        critical = self._make_impact(impact_level="critical")
        low = self._make_impact(impact_level="low")
        assert critical.calculate_urgency_score() > low.calculate_urgency_score()

    def test_urgency_decays_with_time(self):
        now = datetime.utcnow()
        recent = self._make_impact(rss_published_date=now)
        old = self._make_impact(rss_published_date=now - timedelta(hours=48))
        assert recent.calculate_urgency_score() > old.calculate_urgency_score()

    def test_urgency_unknown_impact_level(self):
        impact = self._make_impact(impact_level="unknown")
        score = impact.calculate_urgency_score()
        # Uses default weight of 0.2
        assert score > Decimal("0")


class TestRSSFAQImpactToDict:
    """Tests for RSSFAQImpact.to_dict()."""

    def test_returns_expected_keys(self):
        now = datetime.utcnow()
        impact = RSSFAQImpact(
            faq_id=uuid4(),
            rss_update_id=uuid4(),
            impact_level="high",
            impact_score=Decimal("0.85"),
            confidence_score=Decimal("0.90"),
            rss_source="gazzetta",
            rss_title="Test",
            rss_published_date=now,
            action_required="review",
            processed=False,
            created_at=now,
            matching_tags=["tax"],
            matching_keywords=["irpef"],
            regulatory_changes=["art. 1"],
        )
        result = impact.to_dict()
        expected_keys = {
            "id",
            "faq_id",
            "rss_update_id",
            "impact_level",
            "impact_score",
            "confidence_score",
            "rss_source",
            "rss_title",
            "rss_published_date",
            "matching_tags",
            "regulatory_changes",
            "action_required",
            "action_taken",
            "processed",
            "requires_immediate_action",
            "urgency_score",
            "created_at",
        }
        assert set(result.keys()) == expected_keys


# ──────────────────────────────────────────────────────────────
# FAQGenerationJob model
# ──────────────────────────────────────────────────────────────


class TestFAQGenerationJobCanRetry:
    """Tests for FAQGenerationJob.can_retry()."""

    def _make_job(self, **overrides):
        now = datetime.utcnow()
        defaults = {
            "job_type": "generation",
            "job_name": "Test Job",
            "status": "failed",
            "retry_count": 0,
            "max_retries": 3,
            "created_at": now,
            "parameters": {},
            "output_references": [],
        }
        defaults.update(overrides)
        return FAQGenerationJob(**defaults)

    def test_can_retry_failed_with_retries_left(self):
        job = self._make_job(status="failed", retry_count=1, max_retries=3)
        assert job.can_retry() is True

    def test_cannot_retry_max_retries_reached(self):
        job = self._make_job(status="failed", retry_count=3, max_retries=3)
        assert job.can_retry() is False

    def test_cannot_retry_completed_status(self):
        job = self._make_job(status="completed")
        assert job.can_retry() is False

    def test_cannot_retry_pending_status(self):
        job = self._make_job(status="pending")
        assert job.can_retry() is False


class TestFAQGenerationJobCalculateSuccessRate:
    """Tests for FAQGenerationJob.calculate_success_rate()."""

    def _make_job(self, **overrides):
        now = datetime.utcnow()
        defaults = {
            "job_type": "generation",
            "job_name": "Test Job",
            "status": "completed",
            "items_processed": 0,
            "items_successful": 0,
            "items_failed": 0,
            "created_at": now,
            "parameters": {},
            "output_references": [],
        }
        defaults.update(overrides)
        return FAQGenerationJob(**defaults)

    def test_success_rate_zero_when_no_items(self):
        job = self._make_job(items_processed=0)
        assert job.calculate_success_rate() == Decimal("0")

    def test_success_rate_full(self):
        job = self._make_job(items_processed=10, items_successful=10)
        assert job.calculate_success_rate() == Decimal("1.0")

    def test_success_rate_partial(self):
        job = self._make_job(items_processed=10, items_successful=7)
        rate = job.calculate_success_rate()
        assert rate == Decimal("0.7")


class TestFAQGenerationJobToDict:
    """Tests for FAQGenerationJob.to_dict()."""

    def test_returns_expected_keys(self):
        now = datetime.utcnow()
        job = FAQGenerationJob(
            job_type="analysis",
            job_name="Analysis run",
            status="pending",
            created_at=now,
            parameters={},
            output_references=[],
        )
        result = job.to_dict()
        expected_keys = {
            "id",
            "job_type",
            "job_name",
            "status",
            "progress_percentage",
            "progress_description",
            "items_processed",
            "items_successful",
            "items_failed",
            "success_rate",
            "total_cost_cents",
            "execution_time_seconds",
            "retry_count",
            "can_retry",
            "created_at",
            "started_at",
            "completed_at",
        }
        assert set(result.keys()) == expected_keys


# ──────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────


class TestCalculateFAQPriority:
    """Tests for calculate_faq_priority()."""

    def test_positive_result_with_valid_inputs(self):
        result = calculate_faq_priority(frequency=100, avg_cost_cents=10, quality_score=0.9)
        assert result > Decimal("0")

    def test_scales_with_frequency(self):
        low = calculate_faq_priority(frequency=10, avg_cost_cents=10, quality_score=0.9)
        high = calculate_faq_priority(frequency=100, avg_cost_cents=10, quality_score=0.9)
        assert high > low

    def test_time_factor(self):
        normal = calculate_faq_priority(frequency=100, avg_cost_cents=10, quality_score=0.9, time_factor=1.0)
        boosted = calculate_faq_priority(frequency=100, avg_cost_cents=10, quality_score=0.9, time_factor=2.0)
        assert boosted > normal

    def test_returns_decimal(self):
        result = calculate_faq_priority(frequency=50, avg_cost_cents=5, quality_score=0.85)
        assert isinstance(result, Decimal)


class TestEstimateGenerationCost:
    """Tests for estimate_generation_cost()."""

    def test_gpt35_cost(self):
        cost = estimate_generation_cost("gpt-3.5-turbo", input_tokens=1000, output_tokens=500)
        expected = Decimal(str((1000 / 1000) * 0.0015 + (500 / 1000) * 0.002))
        assert cost == expected

    def test_gpt4_cost_higher_than_gpt35(self):
        cost_35 = estimate_generation_cost("gpt-3.5-turbo", input_tokens=1000, output_tokens=500)
        cost_4 = estimate_generation_cost("gpt-4", input_tokens=1000, output_tokens=500)
        assert cost_4 > cost_35

    def test_unknown_model_defaults_to_gpt35(self):
        cost_unknown = estimate_generation_cost("claude-3", input_tokens=1000, output_tokens=500)
        cost_35 = estimate_generation_cost("gpt-3.5-turbo", input_tokens=1000, output_tokens=500)
        assert cost_unknown == cost_35

    def test_zero_tokens_zero_cost(self):
        cost = estimate_generation_cost("gpt-3.5-turbo", input_tokens=0, output_tokens=0)
        assert cost == Decimal("0.0")

    def test_returns_decimal(self):
        cost = estimate_generation_cost("gpt-4", input_tokens=500, output_tokens=200)
        assert isinstance(cost, Decimal)


# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────


class TestFAQAutomationConfig:
    """Tests for FAQ_AUTOMATION_CONFIG constant."""

    def test_config_has_expected_top_level_keys(self):
        assert "pattern_analysis" in FAQ_AUTOMATION_CONFIG
        assert "generation" in FAQ_AUTOMATION_CONFIG
        assert "rss_integration" in FAQ_AUTOMATION_CONFIG
        assert "business_rules" in FAQ_AUTOMATION_CONFIG

    def test_pattern_analysis_config(self):
        config = FAQ_AUTOMATION_CONFIG["pattern_analysis"]
        assert config["min_frequency"] == 5
        assert config["similarity_threshold"] == 0.85

    def test_generation_config(self):
        config = FAQ_AUTOMATION_CONFIG["generation"]
        assert config["quality_threshold"] == 0.85
        assert config["auto_approve_threshold"] == 0.95
        assert config["max_generation_attempts"] == 3

    def test_rss_integration_config(self):
        config = FAQ_AUTOMATION_CONFIG["rss_integration"]
        assert config["high_impact_threshold"] == 0.7
        assert config["update_check_hours"] == 4

    def test_business_rules_config(self):
        config = FAQ_AUTOMATION_CONFIG["business_rules"]
        assert config["min_roi_score"] == 0.5
        assert config["max_candidates_per_run"] == 20
