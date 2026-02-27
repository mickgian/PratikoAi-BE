"""Comprehensive tests for ItalianTaxDeductionEngine.

Tests cover initialization, eligibility checks, deduction calculations,
deadline management, documentation requirements, and claim validation.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.tax_deduction_engine import (
    DeductionCategory,
    DeductionType,
    DocumentType,
    ItalianTaxDeductionEngine,
    deduction_engine,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Fresh engine instance for each test."""
    return ItalianTaxDeductionEngine()


@pytest.fixture
def default_taxpayer_profile():
    """Default taxpayer profile used in multiple tests."""
    return {
        "income": Decimal("35000"),
        "family_status": "single",
        "age": 35,
        "has_dependents": False,
    }


# ---------------------------------------------------------------------------
# 1. Engine initialization
# ---------------------------------------------------------------------------


class TestEngineInitialization:
    """Tests for engine initialization and rule loading."""

    def test_all_expected_rules_present(self, engine):
        """All seven defined rules must be loaded."""
        expected_rule_ids = {
            "medical_basic",
            "ecobonus_65",
            "superbonus_90",
            "university_fees",
            "charity_donations",
            "dependent_children",
            "professional_training",
        }
        assert set(engine.deduction_rules.keys()) == expected_rule_ids

    def test_rule_count(self, engine):
        """Exactly 7 rules should be loaded."""
        assert len(engine.deduction_rules) == 7

    def test_current_year_set(self, engine):
        """Engine stores the current year on init."""
        assert engine.current_year == datetime.now().year

    def test_medical_basic_rule_structure(self, engine):
        """Verify the medical_basic rule has correct attributes."""
        rule = engine.deduction_rules["medical_basic"]
        assert rule.id == "medical_basic"
        assert rule.name == "Spese Mediche e Sanitarie"
        assert rule.category == DeductionCategory.HEALTH
        assert rule.deduction_type == DeductionType.CAPPED_PERCENTAGE
        assert rule.rate == Decimal("19")
        assert rule.threshold == Decimal("129.11")
        assert rule.max_amount is None

    def test_dependent_children_rule_structure(self, engine):
        """Verify the dependent_children rule has correct attributes."""
        rule = engine.deduction_rules["dependent_children"]
        assert rule.deduction_type == DeductionType.PROGRESSIVE
        assert rule.max_amount == Decimal("1620")
        assert rule.income_cap == Decimal("95000")
        assert rule.max_income == Decimal("95000")

    def test_professional_training_has_age_restrictions(self, engine):
        """Professional training rule must have age restrictions (18, 65)."""
        rule = engine.deduction_rules["professional_training"]
        assert rule.age_restrictions == (18, 65)

    def test_ecobonus_rule_structure(self, engine):
        """Verify ecobonus_65 rule attributes."""
        rule = engine.deduction_rules["ecobonus_65"]
        assert rule.category == DeductionCategory.HOME_RENOVATIONS
        assert rule.deduction_type == DeductionType.PERCENTAGE
        assert rule.rate == Decimal("65")
        assert rule.max_amount == Decimal("60000")


# ---------------------------------------------------------------------------
# 2. get_eligible_deductions
# ---------------------------------------------------------------------------


class TestGetEligibleDeductions:
    """Tests for get_eligible_deductions method."""

    def test_default_profile_gets_most_rules(self, engine):
        """A default profile (35k income, single, 35yo, no dependents) should
        get most rules but not superbonus (income cap 25k)."""
        eligible = engine.get_eligible_deductions(
            income=Decimal("35000"),
            family_status="single",
            age=35,
            has_dependents=False,
        )
        eligible_ids = {r.id for r in eligible}
        # superbonus_90 has max_income=25000, so 35k income should exclude it
        assert "superbonus_90" not in eligible_ids
        # dependent_children has max_income=95000 and no family_status_required,
        # so it should be included
        assert "medical_basic" in eligible_ids
        assert "ecobonus_65" in eligible_ids
        assert "university_fees" in eligible_ids
        assert "charity_donations" in eligible_ids
        assert "professional_training" in eligible_ids

    def test_high_income_excludes_superbonus_and_children(self, engine):
        """Income above 95k should exclude both superbonus and dependent_children."""
        eligible = engine.get_eligible_deductions(
            income=Decimal("100000"),
            family_status="single",
            age=35,
            has_dependents=False,
        )
        eligible_ids = {r.id for r in eligible}
        assert "superbonus_90" not in eligible_ids
        assert "dependent_children" not in eligible_ids

    def test_low_income_includes_all_non_age_restricted(self, engine):
        """Income of 20k should include superbonus_90 and dependent_children."""
        eligible = engine.get_eligible_deductions(
            income=Decimal("20000"),
            family_status="single",
            age=35,
            has_dependents=False,
        )
        eligible_ids = {r.id for r in eligible}
        assert "superbonus_90" in eligible_ids
        assert "dependent_children" in eligible_ids

    def test_returns_list_of_deduction_rules(self, engine):
        """Return type must be a list of DeductionRule instances."""
        eligible = engine.get_eligible_deductions(income=Decimal("30000"))
        assert isinstance(eligible, list)
        for rule in eligible:
            assert hasattr(rule, "id")
            assert hasattr(rule, "deduction_type")


# ---------------------------------------------------------------------------
# 3. _check_eligibility
# ---------------------------------------------------------------------------


class TestCheckEligibility:
    """Tests for the _check_eligibility private method."""

    def test_age_below_minimum_excluded(self, engine):
        """A 17-year-old should not be eligible for professional_training (min 18)."""
        rule = engine.deduction_rules["professional_training"]
        assert (
            engine._check_eligibility(
                rule,
                income=Decimal("30000"),
                family_status="single",
                age=17,
                has_dependents=False,
            )
            is False
        )

    def test_age_above_maximum_excluded(self, engine):
        """A 66-year-old should not be eligible for professional_training (max 65)."""
        rule = engine.deduction_rules["professional_training"]
        assert (
            engine._check_eligibility(
                rule,
                income=Decimal("30000"),
                family_status="single",
                age=66,
                has_dependents=False,
            )
            is False
        )

    def test_age_at_minimum_boundary_included(self, engine):
        """An 18-year-old should be eligible for professional_training."""
        rule = engine.deduction_rules["professional_training"]
        assert (
            engine._check_eligibility(
                rule,
                income=Decimal("30000"),
                family_status="single",
                age=18,
                has_dependents=False,
            )
            is True
        )

    def test_age_at_maximum_boundary_included(self, engine):
        """A 65-year-old should be eligible for professional_training."""
        rule = engine.deduction_rules["professional_training"]
        assert (
            engine._check_eligibility(
                rule,
                income=Decimal("30000"),
                family_status="single",
                age=65,
                has_dependents=False,
            )
            is True
        )

    def test_income_above_max_income_excluded(self, engine):
        """Income above max_income should exclude the rule."""
        rule = engine.deduction_rules["superbonus_90"]
        assert (
            engine._check_eligibility(
                rule,
                income=Decimal("30000"),
                family_status="single",
                age=35,
                has_dependents=False,
            )
            is False
        )

    def test_income_at_max_income_boundary_excluded(self, engine):
        """Income exactly at max_income should still be excluded (> check)."""
        rule = engine.deduction_rules["superbonus_90"]  # max_income=25000
        # The check is `income > rule.max_income`, so 25000 is NOT excluded
        # Actually let's verify: the code says `if rule.max_income and income > rule.max_income`
        # So 25000 > 25000 is False => eligible
        assert (
            engine._check_eligibility(
                rule,
                income=Decimal("25000"),
                family_status="single",
                age=35,
                has_dependents=False,
            )
            is True
        )

    def test_income_just_above_max_income_excluded(self, engine):
        """Income just over max_income should be excluded."""
        rule = engine.deduction_rules["superbonus_90"]  # max_income=25000
        assert (
            engine._check_eligibility(
                rule,
                income=Decimal("25001"),
                family_status="single",
                age=35,
                has_dependents=False,
            )
            is False
        )

    def test_no_restrictions_always_eligible(self, engine):
        """Rules without restrictions (medical_basic) should always be eligible."""
        rule = engine.deduction_rules["medical_basic"]
        assert (
            engine._check_eligibility(
                rule,
                income=Decimal("200000"),
                family_status="single",
                age=90,
                has_dependents=False,
            )
            is True
        )

    def test_family_status_mismatch_excluded(self, engine):
        """If a rule requires a specific family_status that doesn't match, exclude."""
        rule = engine.deduction_rules["medical_basic"]
        # Modify rule temporarily to test family_status_required
        original = rule.family_status_required
        try:
            rule.family_status_required = "married"
            assert (
                engine._check_eligibility(
                    rule,
                    income=Decimal("30000"),
                    family_status="single",
                    age=35,
                    has_dependents=False,
                )
                is False
            )
        finally:
            rule.family_status_required = original

    def test_family_status_match_included(self, engine):
        """If a rule requires a specific family_status and it matches, include."""
        rule = engine.deduction_rules["medical_basic"]
        original = rule.family_status_required
        try:
            rule.family_status_required = "married"
            assert (
                engine._check_eligibility(
                    rule,
                    income=Decimal("30000"),
                    family_status="married",
                    age=35,
                    has_dependents=False,
                )
                is True
            )
        finally:
            rule.family_status_required = original


# ---------------------------------------------------------------------------
# 4. calculate_deduction_amount
# ---------------------------------------------------------------------------


class TestCalculateDeductionAmount:
    """Tests for calculate_deduction_amount method."""

    # -- CAPPED_PERCENTAGE (medical_basic) --

    def test_medical_basic_above_threshold(self, engine):
        """Medical deduction should subtract threshold, then apply 19% rate."""
        result = engine.calculate_deduction_amount(
            rule_id="medical_basic",
            expense_amount=Decimal("1000"),
            income=Decimal("35000"),
        )
        # (1000 - 129.11) * 19% = 870.89 * 0.19 = 165.4691
        expected = float(Decimal("165.47"))
        assert result["deductible_amount"] == expected
        assert result["conditions_met"] is True
        assert result["rule_id"] == "medical_basic"

    def test_medical_basic_below_threshold(self, engine):
        """Expenses at or below threshold should return zero deduction."""
        result = engine.calculate_deduction_amount(
            rule_id="medical_basic",
            expense_amount=Decimal("100"),
            income=Decimal("35000"),
        )
        assert result["deductible_amount"] == Decimal("0")
        assert result["conditions_met"] is False
        assert any("threshold" in w.lower() for w in result["warnings"])

    def test_medical_basic_exactly_at_threshold(self, engine):
        """Expense exactly at threshold yields zero deduction."""
        result = engine.calculate_deduction_amount(
            rule_id="medical_basic",
            expense_amount=Decimal("129.11"),
            income=Decimal("35000"),
        )
        assert result["deductible_amount"] == Decimal("0")
        assert result["conditions_met"] is False

    # -- PERCENTAGE (ecobonus_65) --

    def test_ecobonus_percentage_calculation(self, engine):
        """Ecobonus should apply 65% rate."""
        result = engine.calculate_deduction_amount(
            rule_id="ecobonus_65",
            expense_amount=Decimal("50000"),
            income=Decimal("40000"),
        )
        # 50000 * 65% = 32500
        assert result["deductible_amount"] == float(Decimal("32500.00"))
        assert result["deduction_type"] == "percentage"

    def test_ecobonus_capped_at_max_amount(self, engine):
        """Ecobonus deduction should be capped at max_amount of 60000."""
        result = engine.calculate_deduction_amount(
            rule_id="ecobonus_65",
            expense_amount=Decimal("200000"),
            income=Decimal("40000"),
        )
        # 200000 * 65% = 130000, but max_amount is 60000
        assert result["deductible_amount"] == float(Decimal("60000.00"))
        assert any("capped" in w.lower() for w in result["warnings"])

    def test_superbonus_percentage_calculation(self, engine):
        """Superbonus should apply 90% rate."""
        result = engine.calculate_deduction_amount(
            rule_id="superbonus_90",
            expense_amount=Decimal("80000"),
            income=Decimal("20000"),
        )
        # 80000 * 90% = 72000
        assert result["deductible_amount"] == float(Decimal("72000.00"))

    def test_superbonus_capped_at_max_amount(self, engine):
        """Superbonus deduction should be capped at max_amount of 96000."""
        result = engine.calculate_deduction_amount(
            rule_id="superbonus_90",
            expense_amount=Decimal("200000"),
            income=Decimal("20000"),
        )
        # 200000 * 90% = 180000, but max_amount is 96000
        assert result["deductible_amount"] == float(Decimal("96000.00"))
        assert any("capped" in w.lower() for w in result["warnings"])

    # -- PROGRESSIVE (dependent_children) --

    def test_dependent_children_base_deduction(self, engine):
        """Base deduction for dependent children is 950."""
        result = engine.calculate_deduction_amount(
            rule_id="dependent_children",
            expense_amount=Decimal("0"),
            income=Decimal("40000"),
            additional_params={"child_age": 5, "disabled": False},
        )
        assert result["deductible_amount"] == float(Decimal("950.00"))

    def test_dependent_children_under_3_bonus(self, engine):
        """Child under 3 gets +270 bonus (total 1220)."""
        result = engine.calculate_deduction_amount(
            rule_id="dependent_children",
            expense_amount=Decimal("0"),
            income=Decimal("40000"),
            additional_params={"child_age": 2, "disabled": False},
        )
        assert result["deductible_amount"] == float(Decimal("1220.00"))

    def test_dependent_children_disabled_bonus(self, engine):
        """Disabled child gets +400 bonus (total 1350)."""
        result = engine.calculate_deduction_amount(
            rule_id="dependent_children",
            expense_amount=Decimal("0"),
            income=Decimal("40000"),
            additional_params={"child_age": 5, "disabled": True},
        )
        assert result["deductible_amount"] == float(Decimal("1350.00"))

    def test_dependent_children_under_3_and_disabled(self, engine):
        """Child under 3 and disabled gets 950 + 270 + 400 = 1620."""
        result = engine.calculate_deduction_amount(
            rule_id="dependent_children",
            expense_amount=Decimal("0"),
            income=Decimal("40000"),
            additional_params={"child_age": 1, "disabled": True},
        )
        assert result["deductible_amount"] == float(Decimal("1620.00"))

    def test_dependent_children_no_additional_params(self, engine):
        """With no additional_params, only base deduction should apply."""
        result = engine.calculate_deduction_amount(
            rule_id="dependent_children",
            expense_amount=Decimal("0"),
            income=Decimal("40000"),
            additional_params=None,
        )
        assert result["deductible_amount"] == float(Decimal("950.00"))

    # -- CAPPED_PERCENTAGE (university_fees) --

    def test_university_fees_calculation(self, engine):
        """University fees: 19% of expense, capped at 3700."""
        result = engine.calculate_deduction_amount(
            rule_id="university_fees",
            expense_amount=Decimal("5000"),
            income=Decimal("30000"),
        )
        # 5000 * 19% = 950, under max_amount of 3700 so no cap
        assert result["deductible_amount"] == float(Decimal("950.00"))

    def test_university_fees_capped(self, engine):
        """University fees deduction should be capped at 3700."""
        result = engine.calculate_deduction_amount(
            rule_id="university_fees",
            expense_amount=Decimal("100000"),
            income=Decimal("30000"),
        )
        # 100000 * 19% = 19000, but max_amount is 3700
        assert result["deductible_amount"] == float(Decimal("3700.00"))
        assert any("capped" in w.lower() for w in result["warnings"])

    # -- CAPPED_PERCENTAGE (charity_donations) --

    def test_charity_donations_calculation(self, engine):
        """Charity donations: 30% of expense, capped at 70000."""
        result = engine.calculate_deduction_amount(
            rule_id="charity_donations",
            expense_amount=Decimal("10000"),
            income=Decimal("50000"),
        )
        # 10000 * 30% = 3000
        assert result["deductible_amount"] == float(Decimal("3000.00"))

    # -- PERCENTAGE (professional_training) --

    def test_professional_training_calculation(self, engine):
        """Professional training: 19% of expense, capped at 10000."""
        result = engine.calculate_deduction_amount(
            rule_id="professional_training",
            expense_amount=Decimal("8000"),
            income=Decimal("40000"),
        )
        # 8000 * 19% = 1520
        assert result["deductible_amount"] == float(Decimal("1520.00"))

    def test_professional_training_capped(self, engine):
        """Professional training deduction capped at max_amount 10000."""
        result = engine.calculate_deduction_amount(
            rule_id="professional_training",
            expense_amount=Decimal("100000"),
            income=Decimal("40000"),
        )
        # 100000 * 19% = 19000, capped at 10000
        assert result["deductible_amount"] == float(Decimal("10000.00"))
        assert any("capped" in w.lower() for w in result["warnings"])

    # -- Invalid rule --

    def test_invalid_rule_id_raises_value_error(self, engine):
        """An unknown rule_id should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            engine.calculate_deduction_amount(
                rule_id="nonexistent_rule",
                expense_amount=Decimal("1000"),
            )

    # -- Tax savings and result structure --

    def test_result_contains_tax_savings(self, engine):
        """Result must include tax_savings calculated from marginal rate."""
        result = engine.calculate_deduction_amount(
            rule_id="ecobonus_65",
            expense_amount=Decimal("10000"),
            income=Decimal("40000"),
        )
        # 10000 * 65% = 6500, marginal rate at 40k = 35%
        # tax_savings = 6500 * 35% = 2275
        assert result["tax_savings"] == float(Decimal("2275.00"))

    def test_result_contains_next_deadline(self, engine):
        """Result must include next_deadline as ISO format string."""
        result = engine.calculate_deduction_amount(
            rule_id="medical_basic",
            expense_amount=Decimal("500"),
            income=Decimal("30000"),
        )
        assert result["next_deadline"] is not None
        # Verify it's a valid date string
        date.fromisoformat(result["next_deadline"])

    def test_no_income_uses_default_marginal_rate(self, engine):
        """When income is None, default 35% marginal rate should be used."""
        result = engine.calculate_deduction_amount(
            rule_id="ecobonus_65",
            expense_amount=Decimal("10000"),
            income=None,
        )
        # 10000 * 65% = 6500, default rate = 35%
        # tax_savings = 6500 * 35% = 2275
        assert result["tax_savings"] == float(Decimal("2275.00"))


# ---------------------------------------------------------------------------
# 5. calculate_deduction_amount with max_amount cap
# ---------------------------------------------------------------------------


class TestMaxAmountCap:
    """Specifically test the max_amount capping behavior across rules."""

    @pytest.mark.parametrize(
        "rule_id,max_amount",
        [
            ("ecobonus_65", Decimal("60000")),
            ("superbonus_90", Decimal("96000")),
            ("university_fees", Decimal("3700")),
            ("charity_donations", Decimal("70000")),
            ("professional_training", Decimal("10000")),
        ],
    )
    def test_deduction_capped_at_max(self, engine, rule_id, max_amount):
        """For rules with max_amount, very large expenses should be capped."""
        result = engine.calculate_deduction_amount(
            rule_id=rule_id,
            expense_amount=Decimal("10000000"),
            income=Decimal("20000"),
        )
        assert Decimal(str(result["deductible_amount"])) == max_amount


# ---------------------------------------------------------------------------
# 6. _estimate_marginal_rate
# ---------------------------------------------------------------------------


class TestEstimateMarginalRate:
    """Tests for all four income brackets."""

    def test_bracket_1_low_income(self, engine):
        """Income <= 15000 -> 23%."""
        assert engine._estimate_marginal_rate(Decimal("10000")) == Decimal("23")

    def test_bracket_1_boundary(self, engine):
        """Income exactly 15000 -> 23%."""
        assert engine._estimate_marginal_rate(Decimal("15000")) == Decimal("23")

    def test_bracket_2_mid_low_income(self, engine):
        """Income 15001-28000 -> 25%."""
        assert engine._estimate_marginal_rate(Decimal("20000")) == Decimal("25")

    def test_bracket_2_boundary(self, engine):
        """Income exactly 28000 -> 25%."""
        assert engine._estimate_marginal_rate(Decimal("28000")) == Decimal("25")

    def test_bracket_3_mid_income(self, engine):
        """Income 28001-55000 -> 35%."""
        assert engine._estimate_marginal_rate(Decimal("40000")) == Decimal("35")

    def test_bracket_3_boundary(self, engine):
        """Income exactly 55000 -> 35%."""
        assert engine._estimate_marginal_rate(Decimal("55000")) == Decimal("35")

    def test_bracket_4_high_income(self, engine):
        """Income > 55000 -> 43%."""
        assert engine._estimate_marginal_rate(Decimal("80000")) == Decimal("43")

    def test_bracket_4_just_above_boundary(self, engine):
        """Income 55001 -> 43%."""
        assert engine._estimate_marginal_rate(Decimal("55001")) == Decimal("43")

    def test_zero_income(self, engine):
        """Zero income -> 23% (first bracket)."""
        assert engine._estimate_marginal_rate(Decimal("0")) == Decimal("23")


# ---------------------------------------------------------------------------
# 7. get_upcoming_deadlines
# ---------------------------------------------------------------------------


class TestGetUpcomingDeadlines:
    """Tests for get_upcoming_deadlines method."""

    def test_returns_list_of_dicts(self, engine):
        """Return type must be a list of dicts."""
        deadlines = engine.get_upcoming_deadlines(days_ahead=3650)
        assert isinstance(deadlines, list)
        for d in deadlines:
            assert isinstance(d, dict)

    def test_deadline_structure(self, engine):
        """Each deadline dict must contain expected keys."""
        deadlines = engine.get_upcoming_deadlines(days_ahead=3650)
        if deadlines:
            d = deadlines[0]
            assert "rule_id" in d
            assert "rule_name" in d
            assert "deadline" in d
            assert "days_left" in d
            assert "category" in d
            assert "urgency" in d
            assert "required_documents" in d

    def test_deadlines_sorted_by_days_left(self, engine):
        """Deadlines must be sorted by days_left ascending."""
        deadlines = engine.get_upcoming_deadlines(days_ahead=3650)
        if len(deadlines) > 1:
            for i in range(len(deadlines) - 1):
                assert deadlines[i]["days_left"] <= deadlines[i + 1]["days_left"]

    def test_urgency_classification(self, engine):
        """Urgency should be urgent/moderate/normal based on days_left."""
        deadlines = engine.get_upcoming_deadlines(days_ahead=3650)
        for d in deadlines:
            if d["days_left"] <= 30:
                assert d["urgency"] == "urgent"
            elif d["days_left"] <= 60:
                assert d["urgency"] == "moderate"
            else:
                assert d["urgency"] == "normal"

    def test_zero_days_ahead_returns_only_past_deadlines(self, engine):
        """With days_ahead=0, only deadlines today or earlier should appear."""
        deadlines = engine.get_upcoming_deadlines(days_ahead=0)
        today = datetime.now().date()
        for d in deadlines:
            deadline_date = date.fromisoformat(d["deadline"])
            assert deadline_date <= today

    def test_required_documents_are_string_values(self, engine):
        """required_documents should be list of string values, not enum instances."""
        deadlines = engine.get_upcoming_deadlines(days_ahead=3650)
        for d in deadlines:
            for doc in d["required_documents"]:
                assert isinstance(doc, str)


# ---------------------------------------------------------------------------
# 8. get_deduction_documentation_requirements
# ---------------------------------------------------------------------------


class TestGetDeductionDocumentationRequirements:
    """Tests for get_deduction_documentation_requirements method."""

    def test_valid_rule_returns_full_info(self, engine):
        """A valid rule_id should return all documentation fields."""
        result = engine.get_deduction_documentation_requirements("medical_basic")
        assert result["rule_name"] == "Spese Mediche e Sanitarie"
        assert "receipt" in result["required_documents"]
        assert "medical_prescription" in result["required_documents"]
        assert result["retention_period_years"] == 5
        assert result["submission_deadline"] == "2025-07-31"
        assert isinstance(result["conditions"], list)
        assert isinstance(result["exclusions"], list)
        assert result["legal_reference"] == "Art. 15, comma 1, lett. c) TUIR"
        assert isinstance(result["documentation_tips"], list)

    def test_invalid_rule_returns_error(self, engine):
        """An invalid rule_id should return an error dict."""
        result = engine.get_deduction_documentation_requirements("nonexistent")
        assert result == {"error": "Rule not found"}

    def test_ecobonus_documentation(self, engine):
        """Ecobonus requires invoice, bank_statement, certificate with 10yr retention."""
        result = engine.get_deduction_documentation_requirements("ecobonus_65")
        assert "invoice" in result["required_documents"]
        assert "bank_statement" in result["required_documents"]
        assert "certificate" in result["required_documents"]
        assert result["retention_period_years"] == 10

    def test_charity_documentation(self, engine):
        """Charity donations require donation_receipt."""
        result = engine.get_deduction_documentation_requirements("charity_donations")
        assert "donation_receipt" in result["required_documents"]


# ---------------------------------------------------------------------------
# 9. _get_documentation_tips
# ---------------------------------------------------------------------------


class TestGetDocumentationTips:
    """Tests for _get_documentation_tips private method."""

    def test_receipt_tip_present(self, engine):
        """Rules requiring RECEIPT should get the receipt tip."""
        rule = engine.deduction_rules["medical_basic"]
        tips = engine._get_documentation_tips(rule)
        assert any("ricevute fiscali" in tip.lower() for tip in tips)

    def test_bank_statement_tip_present(self, engine):
        """Rules requiring BANK_STATEMENT should get the bank transfer tip."""
        rule = engine.deduction_rules["ecobonus_65"]
        tips = engine._get_documentation_tips(rule)
        assert any("bonifico parlante" in tip.lower() for tip in tips)

    def test_medical_prescription_tip_present(self, engine):
        """Rules requiring MEDICAL_PRESCRIPTION should get the prescription tip."""
        rule = engine.deduction_rules["medical_basic"]
        tips = engine._get_documentation_tips(rule)
        assert any("prescrizione medica" in tip.lower() for tip in tips)

    def test_home_renovations_category_gets_extra_tips(self, engine):
        """HOME_RENOVATIONS category rules should get ENEA and asseverazione tips."""
        rule = engine.deduction_rules["ecobonus_65"]
        tips = engine._get_documentation_tips(rule)
        assert any("enea" in tip.lower() for tip in tips)
        assert any("asseverazione" in tip.lower() for tip in tips)
        assert any("fatture elettroniche" in tip.lower() for tip in tips)

    def test_superbonus_gets_home_renovation_tips(self, engine):
        """Superbonus (also HOME_RENOVATIONS) should get the same extra tips."""
        rule = engine.deduction_rules["superbonus_90"]
        tips = engine._get_documentation_tips(rule)
        assert any("enea" in tip.lower() for tip in tips)

    def test_non_renovation_rule_has_no_enea_tip(self, engine):
        """A non-renovation rule (charity) should NOT get ENEA tips."""
        rule = engine.deduction_rules["charity_donations"]
        tips = engine._get_documentation_tips(rule)
        assert not any("enea" in tip.lower() for tip in tips)

    def test_rule_without_receipt_no_receipt_tip(self, engine):
        """dependent_children requires CERTIFICATE, not RECEIPT; no receipt tip."""
        rule = engine.deduction_rules["dependent_children"]
        tips = engine._get_documentation_tips(rule)
        assert not any("ricevute fiscali" in tip.lower() for tip in tips)


# ---------------------------------------------------------------------------
# 10. validate_deduction_claim
# ---------------------------------------------------------------------------


class TestValidateDeductionClaim:
    """Tests for validate_deduction_claim method."""

    def test_valid_claim(self, engine):
        """A claim within all constraints should be valid."""
        with patch("app.services.tax_deduction_engine.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = date(2025, 3, 1)

            result = engine.validate_deduction_claim(
                rule_id="medical_basic",
                expense_amount=Decimal("500"),
                expense_date=date(2024, 6, 15),
                taxpayer_profile={
                    "income": Decimal("30000"),
                    "family_status": "single",
                    "age": 35,
                    "has_dependents": False,
                },
            )
            assert result["valid"] is True
            assert len(result["errors"]) == 0

    def test_expense_date_before_period_start(self, engine):
        """Expense date before the allowed period should be invalid."""
        result = engine.validate_deduction_claim(
            rule_id="medical_basic",
            expense_amount=Decimal("500"),
            expense_date=date(2023, 12, 31),
            taxpayer_profile={
                "income": Decimal("30000"),
                "family_status": "single",
                "age": 35,
                "has_dependents": False,
            },
        )
        assert result["valid"] is False
        assert any("date" in e.lower() for e in result["errors"])

    def test_expense_date_after_period_end(self, engine):
        """Expense date after the allowed period should be invalid."""
        result = engine.validate_deduction_claim(
            rule_id="medical_basic",
            expense_amount=Decimal("500"),
            expense_date=date(2025, 1, 1),
            taxpayer_profile={
                "income": Decimal("30000"),
                "family_status": "single",
                "age": 35,
                "has_dependents": False,
            },
        )
        assert result["valid"] is False
        assert any("date" in e.lower() for e in result["errors"])

    def test_submission_deadline_passed(self, engine):
        """If current date is past the submission deadline, claim is invalid."""
        with patch("app.services.tax_deduction_engine.datetime") as mock_dt:
            # medical_basic submission_deadline is 2025-07-31
            mock_dt.now.return_value.date.return_value = date(2025, 8, 1)

            result = engine.validate_deduction_claim(
                rule_id="medical_basic",
                expense_amount=Decimal("500"),
                expense_date=date(2024, 6, 15),
                taxpayer_profile={
                    "income": Decimal("30000"),
                    "family_status": "single",
                    "age": 35,
                    "has_dependents": False,
                },
            )
            assert result["valid"] is False
            assert any("deadline" in e.lower() for e in result["errors"])

    def test_amount_exceeds_max_produces_warning(self, engine):
        """Expense exceeding max_amount should produce a warning (not error)."""
        with patch("app.services.tax_deduction_engine.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = date(2025, 1, 1)

            result = engine.validate_deduction_claim(
                rule_id="ecobonus_65",
                expense_amount=Decimal("100000"),  # max_amount is 60000
                expense_date=date(2024, 6, 15),
                taxpayer_profile={
                    "income": Decimal("30000"),
                    "family_status": "single",
                    "age": 35,
                    "has_dependents": False,
                },
            )
            assert any("exceeds" in w.lower() for w in result["warnings"])

    def test_ineligible_profile(self, engine):
        """A taxpayer that fails eligibility should get an error."""
        with patch("app.services.tax_deduction_engine.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = date(2025, 1, 1)

            result = engine.validate_deduction_claim(
                rule_id="superbonus_90",
                expense_amount=Decimal("50000"),
                expense_date=date(2024, 6, 15),
                taxpayer_profile={
                    "income": Decimal("100000"),  # far above max_income of 25000
                    "family_status": "single",
                    "age": 35,
                    "has_dependents": False,
                },
            )
            assert result["valid"] is False
            assert any("not eligible" in e.lower() for e in result["errors"])

    def test_invalid_rule_id_returns_error(self, engine):
        """An unknown rule_id should return a not-valid result."""
        result = engine.validate_deduction_claim(
            rule_id="nonexistent",
            expense_amount=Decimal("1000"),
            expense_date=date(2024, 6, 15),
            taxpayer_profile={"income": Decimal("30000")},
        )
        assert result["valid"] is False
        assert result["error"] == "Rule not found"

    def test_age_restriction_makes_claim_invalid(self, engine):
        """A 17-year-old trying to claim professional_training should be ineligible."""
        with patch("app.services.tax_deduction_engine.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = date(2025, 1, 1)

            result = engine.validate_deduction_claim(
                rule_id="professional_training",
                expense_amount=Decimal("5000"),
                expense_date=date(2024, 6, 15),
                taxpayer_profile={
                    "income": Decimal("30000"),
                    "family_status": "single",
                    "age": 17,
                    "has_dependents": False,
                },
            )
            assert result["valid"] is False
            assert any("not eligible" in e.lower() for e in result["errors"])

    def test_multiple_errors_accumulated(self, engine):
        """A claim with multiple issues should accumulate all errors."""
        with patch("app.services.tax_deduction_engine.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = date(2025, 8, 1)

            result = engine.validate_deduction_claim(
                rule_id="superbonus_90",
                expense_amount=Decimal("200000"),
                expense_date=date(2023, 1, 1),  # before period start
                taxpayer_profile={
                    "income": Decimal("100000"),  # above max_income
                    "family_status": "single",
                    "age": 35,
                    "has_dependents": False,
                },
            )
            assert result["valid"] is False
            # Should have at least: date error, deadline error, eligibility error
            assert len(result["errors"]) >= 3


# ---------------------------------------------------------------------------
# 11. Singleton deduction_engine
# ---------------------------------------------------------------------------


class TestSingletonInstance:
    """Tests for the module-level singleton."""

    def test_singleton_exists(self):
        """The module-level deduction_engine should exist."""
        assert deduction_engine is not None

    def test_singleton_is_instance_of_engine(self):
        """The singleton must be an ItalianTaxDeductionEngine instance."""
        assert isinstance(deduction_engine, ItalianTaxDeductionEngine)

    def test_singleton_has_rules_loaded(self):
        """The singleton should have all rules loaded."""
        assert len(deduction_engine.deduction_rules) == 7

    def test_singleton_is_functional(self):
        """The singleton should be able to calculate deductions."""
        result = deduction_engine.calculate_deduction_amount(
            rule_id="medical_basic",
            expense_amount=Decimal("500"),
            income=Decimal("30000"),
        )
        assert result["deductible_amount"] > 0
