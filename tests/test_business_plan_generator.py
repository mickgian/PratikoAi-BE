"""
TDD Tests for Business Plan Generator.

This module tests comprehensive business plan creation and validation functionality,
including financial projections, market analysis, and strategic planning components.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

import pytest

# These imports will fail initially - that's the TDD approach
from app.services.validators.business_plan_generator import (
    BalanceSheetProjection,
    BusinessPlan,
    BusinessPlanGenerator,
    BusinessSection,
    BusinessStage,
    CashFlowProjection,
    CompetitorAnalysis,
    FinancialModel,
    FinancialProjection,
    Industry,
    MarketAnalysis,
    PlanTemplate,
    ProfitLossProjection,
    ProjectionPeriod,
    RiskAssessment,
    ValidationResult,
)


class TestBusinessPlanGenerator:
    """Test suite for Business Plan Generator using TDD methodology."""

    @pytest.fixture
    def plan_generator(self):
        """Create business plan generator instance for tests."""
        return BusinessPlanGenerator()

    # =========================================================================
    # Core Business Plan Generation Tests
    # =========================================================================

    def test_basic_business_plan_generation_startup(self, plan_generator):
        """Test basic business plan generation for startup company."""
        # Arrange
        company_data = {
            "name": "InnovaTech SRL",
            "industry": Industry.TECHNOLOGY,
            "stage": BusinessStage.STARTUP,
            "founding_date": date(2024, 1, 1),
            "employees": 5,
            "current_revenue": Decimal("50000"),
            "target_market": "SMB Software Solutions",
            "unique_value_proposition": "AI-powered automation for small businesses",
        }

        # Act
        result = plan_generator.generate_business_plan(
            company_data=company_data, projection_years=5, template=PlanTemplate.STARTUP_COMPREHENSIVE
        )

        # Assert
        assert isinstance(result, BusinessPlan)
        assert result.company_name == "InnovaTech SRL"
        assert result.industry == Industry.TECHNOLOGY
        assert result.business_stage == BusinessStage.STARTUP
        assert len(result.sections) >= 8  # Executive Summary, Company Description, Market Analysis, etc.
        assert "executive_summary" in result.sections
        assert "financial_projections" in result.sections
        assert "market_analysis" in result.sections
        assert "competitive_analysis" in result.sections
        assert result.projection_period == 5
        assert len(result.financial_model.years) == 5

    def test_business_plan_generation_existing_company(self, plan_generator):
        """Test business plan generation for existing company expansion."""
        # Arrange
        company_data = {
            "name": "GreenEco Manufacturing SRL",
            "industry": Industry.MANUFACTURING,
            "stage": BusinessStage.GROWTH,
            "founding_date": date(2018, 6, 15),
            "employees": 35,
            "current_revenue": Decimal("2500000"),
            "historical_revenue": [
                {"year": 2021, "revenue": Decimal("1800000")},
                {"year": 2022, "revenue": Decimal("2100000")},
                {"year": 2023, "revenue": Decimal("2300000")},
            ],
            "expansion_plan": "International market entry",
        }

        # Act
        result = plan_generator.generate_business_plan(
            company_data=company_data, projection_years=3, template=PlanTemplate.EXPANSION_FOCUSED
        )

        # Assert
        assert result.business_stage == BusinessStage.GROWTH
        assert result.projection_period == 3
        assert result.historical_analysis is not None
        assert len(result.historical_analysis.revenue_trend) == 3
        assert "expansion_strategy" in result.sections
        assert result.financial_model.base_revenue == Decimal("2500000")

    # =========================================================================
    # Financial Projections Tests
    # =========================================================================

    def test_financial_projections_revenue_growth_model(self, plan_generator):
        """Test financial projections with various revenue growth models."""
        # Arrange
        base_data = {
            "current_revenue": Decimal("1000000"),
            "growth_model": "compound",
            "growth_rates": [Decimal("0.25"), Decimal("0.20"), Decimal("0.15")],  # 25%, 20%, 15%
            "cost_structure": {
                "cogs_percentage": Decimal("0.35"),  # 35% COGS
                "opex_percentage": Decimal("0.45"),  # 45% Operating expenses
                "tax_rate": Decimal("0.24"),  # 24% IRES
            },
        }

        # Expected revenue projections
        expected_revenues = [
            Decimal("1000000"),  # Year 0 (base)
            Decimal("1250000"),  # Year 1: +25%
            Decimal("1500000"),  # Year 2: +20%
            Decimal("1725000"),  # Year 3: +15%
        ]

        # Act
        projections = plan_generator.generate_financial_projections(base_data=base_data, projection_years=3)

        # Assert
        assert isinstance(projections, FinancialProjection)
        assert len(projections.revenue_projections) == 4  # Base + 3 years
        for i, expected_revenue in enumerate(expected_revenues):
            assert projections.revenue_projections[i] == expected_revenue

        # Test P&L calculations
        year_1_pl = projections.profit_loss_projections[1]
        assert year_1_pl.revenue == Decimal("1250000")
        assert year_1_pl.cogs == Decimal("437500")  # 35% of 1.25M
        assert year_1_pl.gross_profit == Decimal("812500")  # Revenue - COGS
        assert year_1_pl.operating_expenses == Decimal("562500")  # 45% of 1.25M
        assert year_1_pl.ebitda == Decimal("250000")  # Gross profit - OpEx

    def test_cash_flow_projections_with_capex(self, plan_generator):
        """Test cash flow projections including capital expenditures."""
        # Arrange
        cash_flow_data = {
            "base_revenue": Decimal("800000"),
            "growth_rate": Decimal("0.15"),  # 15% annual growth
            "cash_conversion_cycle": 60,  # 60 days
            "capex_schedule": [
                {"year": 1, "amount": Decimal("150000"), "description": "New equipment"},
                {"year": 3, "amount": Decimal("100000"), "description": "Facility expansion"},
            ],
            "loan_repayment": Decimal("50000"),  # Annual loan payment
            "working_capital_ratio": Decimal("0.12"),  # 12% of revenue
        }

        # Act
        cash_flow = plan_generator.generate_cash_flow_projections(data=cash_flow_data, projection_years=5)

        # Assert
        assert isinstance(cash_flow, CashFlowProjection)
        assert len(cash_flow.yearly_projections) == 5

        # Year 1 should include CapEx
        year_1 = cash_flow.yearly_projections[0]
        assert year_1.capital_expenditures == Decimal("150000")
        assert year_1.loan_payments == Decimal("50000")
        assert year_1.free_cash_flow < year_1.operating_cash_flow  # Reduced by CapEx

        # Year 3 should include second CapEx
        year_3 = cash_flow.yearly_projections[2]
        assert year_3.capital_expenditures == Decimal("100000")

        # Working capital should scale with revenue
        expected_wc_year_1 = (Decimal("800000") * Decimal("1.15")) * Decimal("0.12")
        assert abs(year_1.working_capital_change - expected_wc_year_1) < Decimal("1000")

    def test_balance_sheet_projections(self, plan_generator):
        """Test balance sheet projections with assets and liabilities."""
        # Arrange
        balance_sheet_data = {
            "starting_balance_sheet": {
                "cash": Decimal("100000"),
                "receivables": Decimal("150000"),
                "inventory": Decimal("200000"),
                "ppe": Decimal("500000"),
                "accounts_payable": Decimal("80000"),
                "debt": Decimal("300000"),
                "equity": Decimal("570000"),
            },
            "revenue_growth": Decimal("0.20"),
            "depreciation_rate": Decimal("0.10"),
            "debt_paydown": Decimal("50000"),  # Annual debt reduction
        }

        # Act
        balance_sheet = plan_generator.generate_balance_sheet_projections(data=balance_sheet_data, projection_years=3)

        # Assert
        assert isinstance(balance_sheet, BalanceSheetProjection)
        assert len(balance_sheet.yearly_projections) == 3

        # Test Year 1 balance sheet
        year_1 = balance_sheet.yearly_projections[0]

        # Assets should grow with business
        assert (
            year_1.total_assets
            > balance_sheet_data["starting_balance_sheet"]["cash"]
            + balance_sheet_data["starting_balance_sheet"]["receivables"]
            + balance_sheet_data["starting_balance_sheet"]["inventory"]
            + balance_sheet_data["starting_balance_sheet"]["ppe"]
        )

        # PPE should decrease due to depreciation
        expected_ppe = Decimal("500000") - (Decimal("500000") * Decimal("0.10"))
        assert abs(year_1.ppe - expected_ppe) < Decimal("1000")

        # Debt should decrease due to paydown
        expected_debt = Decimal("300000") - Decimal("50000")
        assert year_1.debt == expected_debt

        # Balance sheet should balance
        assert abs(year_1.total_assets - (year_1.total_liabilities + year_1.equity)) < Decimal("1")

    # =========================================================================
    # Market Analysis Tests
    # =========================================================================

    def test_market_analysis_generation_tam_sam_som(self, plan_generator):
        """Test market analysis generation with TAM/SAM/SOM calculations."""
        # Arrange
        market_data = {
            "industry": Industry.SAAS,
            "target_geography": ["Italy", "Germany", "France"],
            "customer_segments": ["SMB", "Mid-market"],
            "market_size_data": {
                "tam_eur": Decimal("5000000000"),  # €5B total addressable market
                "penetration_rate": Decimal("0.02"),  # 2% market penetration achievable
                "average_deal_size": Decimal("5000"),  # €5K average annual contract
                "customer_acquisition_rate": Decimal("0.15"),  # 15% annual customer growth
            },
            "competitive_landscape": "Fragmented market with multiple players",
        }

        # Act
        market_analysis = plan_generator.generate_market_analysis(market_data)

        # Assert
        assert isinstance(market_analysis, MarketAnalysis)
        assert market_analysis.tam == Decimal("5000000000")

        # SAM should be subset of TAM based on geography and segments
        assert market_analysis.sam < market_analysis.tam
        assert market_analysis.sam > Decimal("0")

        # SOM should be subset of SAM based on penetration rate
        expected_som = market_analysis.sam * Decimal("0.02")
        assert abs(market_analysis.som - expected_som) < Decimal("10000")

        assert len(market_analysis.target_segments) == 2
        assert "SMB" in market_analysis.target_segments
        assert "Mid-market" in market_analysis.target_segments
        assert len(market_analysis.geographic_markets) == 3

    def test_competitive_analysis_generation(self, plan_generator):
        """Test competitive analysis with competitor positioning."""
        # Arrange
        competitive_data = {
            "direct_competitors": [
                {
                    "name": "CompetitorA SRL",
                    "market_share": Decimal("0.25"),
                    "revenue_estimate": Decimal("50000000"),
                    "strengths": ["Brand recognition", "Large customer base"],
                    "weaknesses": ["Legacy technology", "High prices"],
                },
                {
                    "name": "CompetitorB SpA",
                    "market_share": Decimal("0.15"),
                    "revenue_estimate": Decimal("30000000"),
                    "strengths": ["Innovation", "Customer service"],
                    "weaknesses": ["Limited market presence", "Small team"],
                },
            ],
            "indirect_competitors": ["Traditional consulting firms", "In-house solutions"],
            "competitive_advantages": ["AI-powered automation", "Cost-effective pricing", "Rapid implementation"],
        }

        # Act
        competitive_analysis = plan_generator.generate_competitive_analysis(competitive_data)

        # Assert
        assert isinstance(competitive_analysis, CompetitorAnalysis)
        assert len(competitive_analysis.direct_competitors) == 2
        assert len(competitive_analysis.indirect_competitors) == 2
        assert len(competitive_analysis.competitive_advantages) == 3

        # Test competitor details
        competitor_a = competitive_analysis.direct_competitors[0]
        assert competitor_a.name == "CompetitorA SRL"
        assert competitor_a.market_share == Decimal("0.25")
        assert len(competitor_a.strengths) == 2
        assert len(competitor_a.weaknesses) == 2

        # Test market positioning
        assert competitive_analysis.market_positioning is not None
        assert competitive_analysis.differentiation_strategy is not None

    # =========================================================================
    # Risk Assessment Tests
    # =========================================================================

    def test_risk_assessment_generation_comprehensive(self, plan_generator):
        """Test comprehensive risk assessment generation."""
        # Arrange
        risk_data = {
            "business_stage": BusinessStage.GROWTH,
            "industry": Industry.FINTECH,
            "revenue_concentration": {
                "top_3_customers_percentage": Decimal("0.45"),  # 45% revenue concentration
                "largest_customer_percentage": Decimal("0.25"),  # 25% from largest customer
            },
            "geographic_concentration": {
                "domestic_percentage": Decimal("0.80"),  # 80% domestic revenue
                "top_market_dependency": "Italy",
            },
            "regulatory_environment": "Highly regulated financial services",
            "technology_dependencies": ["Cloud infrastructure", "Third-party APIs"],
            "key_personnel": ["CEO", "CTO", "Head of Sales"],
        }

        # Act
        risk_assessment = plan_generator.generate_risk_assessment(risk_data)

        # Assert
        assert isinstance(risk_assessment, RiskAssessment)
        assert len(risk_assessment.identified_risks) >= 5

        # Should identify customer concentration risk
        customer_risk = next(
            (r for r in risk_assessment.identified_risks if "customer concentration" in r.description.lower()), None
        )
        assert customer_risk is not None
        assert customer_risk.severity in ["High", "Medium"]
        assert customer_risk.probability > Decimal("0.3")

        # Should identify regulatory risk for fintech
        regulatory_risk = next(
            (r for r in risk_assessment.identified_risks if "regulatory" in r.description.lower()), None
        )
        assert regulatory_risk is not None

        # Should have mitigation strategies
        assert len(risk_assessment.mitigation_strategies) >= 3
        assert all(strategy.risk_category for strategy in risk_assessment.mitigation_strategies)

        # Overall risk score should be calculated
        assert Decimal("0") <= risk_assessment.overall_risk_score <= Decimal("10")

    def test_risk_assessment_scenario_analysis(self, plan_generator):
        """Test risk assessment with scenario analysis."""
        # Arrange
        scenario_data = {
            "base_case": {"revenue_growth": Decimal("0.20"), "market_conditions": "stable"},
            "bear_case": {
                "revenue_decline": Decimal("-0.15"),
                "market_conditions": "recession",
                "customer_churn_increase": Decimal("0.30"),
            },
            "bull_case": {
                "revenue_growth": Decimal("0.40"),
                "market_conditions": "expansion",
                "market_share_gain": Decimal("0.10"),
            },
        }

        # Act
        scenario_analysis = plan_generator.generate_scenario_analysis(scenario_data)

        # Assert
        assert "base_case" in scenario_analysis.scenarios
        assert "bear_case" in scenario_analysis.scenarios
        assert "bull_case" in scenario_analysis.scenarios

        # Each scenario should have financial impact
        for _scenario_name, scenario in scenario_analysis.scenarios.items():
            assert scenario.revenue_impact is not None
            assert scenario.probability > Decimal("0")
            assert scenario.financial_model is not None

        # Bear case should show negative impact
        assert scenario_analysis.scenarios["bear_case"].revenue_impact < Decimal("0")
        # Bull case should show positive impact
        assert scenario_analysis.scenarios["bull_case"].revenue_impact > Decimal("0")

    # =========================================================================
    # Business Plan Validation Tests
    # =========================================================================

    def test_business_plan_validation_comprehensive(self, plan_generator):
        """Test comprehensive business plan validation."""
        # Arrange - Create a complete business plan
        company_data = {
            "name": "TechStart SRL",
            "industry": Industry.TECHNOLOGY,
            "stage": BusinessStage.STARTUP,
            "current_revenue": Decimal("100000"),
            "projection_years": 5,
        }

        business_plan = plan_generator.generate_business_plan(
            company_data=company_data, projection_years=5, template=PlanTemplate.STARTUP_COMPREHENSIVE
        )

        # Act
        validation_result = plan_generator.validate_business_plan(business_plan)

        # Assert
        assert isinstance(validation_result, ValidationResult)
        assert validation_result.is_valid is not None
        assert len(validation_result.validation_checks) >= 10

        # Should validate financial consistency
        financial_check = next(
            (c for c in validation_result.validation_checks if "financial" in c.check_name.lower()), None
        )
        assert financial_check is not None

        # Should validate market assumptions
        market_check = next((c for c in validation_result.validation_checks if "market" in c.check_name.lower()), None)
        assert market_check is not None

        # Should provide overall score
        assert Decimal("0") <= validation_result.overall_score <= Decimal("100")

        # Should have recommendations if issues found
        if not validation_result.is_valid:
            assert len(validation_result.recommendations) > 0

    def test_business_plan_validation_financial_consistency(self, plan_generator):
        """Test business plan validation for financial consistency."""
        # Arrange - Create plan with intentional inconsistencies
        inconsistent_data = {
            "revenue_projections": [Decimal("100000"), Decimal("90000")],  # Revenue declining
            "growth_assumptions": [Decimal("0.20")],  # But assuming 20% growth
            "cash_flow": [Decimal("-50000"), Decimal("-80000")],  # Negative cash flow
            "funding_requirements": Decimal("0"),  # But no funding planned
        }

        # Act
        financial_validation = plan_generator.validate_financial_consistency(inconsistent_data)

        # Assert
        assert not financial_validation.is_consistent
        assert len(financial_validation.inconsistencies) >= 2

        # Should identify revenue/growth mismatch
        revenue_issue = next(
            (i for i in financial_validation.inconsistencies if "revenue" in i.issue_type.lower()), None
        )
        assert revenue_issue is not None

        # Should identify funding gap
        funding_issue = next(
            (i for i in financial_validation.inconsistencies if "funding" in i.issue_type.lower()), None
        )
        assert funding_issue is not None

    # =========================================================================
    # Template and Formatting Tests
    # =========================================================================

    def test_business_plan_template_startup(self, plan_generator):
        """Test startup business plan template generation."""
        # Arrange
        template_data = {
            "template": PlanTemplate.STARTUP_COMPREHENSIVE,
            "company_stage": BusinessStage.STARTUP,
            "funding_round": "Seed",
            "funding_target": Decimal("500000"),
        }

        # Act
        template = plan_generator.get_business_plan_template(template_data)

        # Assert
        startup_sections = [
            "executive_summary",
            "company_description",
            "market_analysis",
            "product_service_description",
            "marketing_sales_strategy",
            "management_team",
            "financial_projections",
            "funding_request",
            "appendices",
        ]

        assert all(section in template.sections for section in startup_sections)
        assert template.recommended_length["executive_summary"] <= 2  # Max 2 pages
        assert template.required_financial_statements == ["P&L", "Cash Flow", "Balance Sheet", "Break-even Analysis"]

    def test_business_plan_export_pdf_format(self, plan_generator):
        """Test business plan export to PDF format."""
        # Arrange
        company_data = {"name": "ExportTest SRL", "industry": Industry.RETAIL, "stage": BusinessStage.STARTUP}

        business_plan = plan_generator.generate_business_plan(company_data)

        # Act
        pdf_export = plan_generator.export_business_plan(
            business_plan=business_plan, format="pdf", include_appendices=True
        )

        # Assert
        assert pdf_export.format == "pdf"
        assert pdf_export.file_size > 0
        assert pdf_export.page_count >= 15  # Comprehensive plan should be substantial
        assert pdf_export.sections_included >= 8
        assert pdf_export.financial_charts_included >= 3  # Revenue, cash flow, etc.

    # =========================================================================
    # Performance and Integration Tests
    # =========================================================================

    def test_business_plan_generation_performance(self, plan_generator):
        """Test business plan generation performance."""
        import time

        # Arrange
        company_data = {
            "name": "PerformanceTest SRL",
            "industry": Industry.MANUFACTURING,
            "stage": BusinessStage.GROWTH,
            "current_revenue": Decimal("5000000"),
            "employees": 50,
        }

        # Act
        start_time = time.time()
        business_plan = plan_generator.generate_business_plan(
            company_data=company_data,
            projection_years=10,  # Longer projection period
            template=PlanTemplate.COMPREHENSIVE_ENTERPRISE,
        )
        end_time = time.time()

        # Assert
        generation_time = end_time - start_time
        assert generation_time < 30.0  # Should complete in under 30 seconds
        assert business_plan.generation_metadata.processing_time < 30000  # milliseconds
        assert business_plan.generation_metadata.sections_generated >= 10
        assert len(business_plan.financial_model.years) == 10

    def test_business_plan_italian_compliance(self, plan_generator):
        """Test business plan generation for Italian regulatory compliance."""
        # Arrange
        italian_company_data = {
            "name": "Compliance Test SRL",
            "legal_form": "SRL",
            "industry": Industry.FINTECH,
            "jurisdiction": "Italy",
            "regulatory_requirements": ["GDPR", "PSD2", "Italian Corporate Law"],
            "tax_optimization": True,
        }

        # Act
        italian_plan = plan_generator.generate_business_plan(
            company_data=italian_company_data, template=PlanTemplate.ITALIAN_REGULATORY_COMPLIANT
        )

        # Assert
        assert "regulatory_compliance" in italian_plan.sections
        assert "italian_tax_structure" in italian_plan.sections
        assert italian_plan.compliance_checklist is not None

        # Should include Italian-specific sections
        regulatory_section = italian_plan.sections["regulatory_compliance"]
        assert "GDPR compliance" in regulatory_section.content.lower()
        assert "italian corporate governance" in regulatory_section.content.lower()

        # Financial projections should use Italian tax rates
        tax_assumptions = italian_plan.financial_model.tax_assumptions
        assert tax_assumptions.corporate_tax_rate == Decimal("0.24")  # IRES 24%
        assert tax_assumptions.regional_tax_rate == Decimal("0.039")  # IRAP 3.9%

    # =========================================================================
    # Error Handling and Edge Cases
    # =========================================================================

    def test_business_plan_generation_missing_data(self, plan_generator):
        """Test business plan generation with missing critical data."""
        # Arrange
        incomplete_data = {
            "name": "Incomplete SRL",
            # Missing industry, stage, revenue, etc.
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Missing required company data"):
            plan_generator.generate_business_plan(incomplete_data)

    def test_business_plan_validation_edge_cases(self, plan_generator):
        """Test business plan validation with edge cases."""
        # Arrange - Extreme scenarios
        edge_case_data = {
            "revenue_projections": [Decimal("1000000"), Decimal("10000000")],  # 10x growth
            "market_share_target": Decimal("0.95"),  # 95% market share (unrealistic)
            "employee_growth": [5, 500],  # 100x employee growth
            "profit_margins": [Decimal("-0.5"), Decimal("0.8")],  # -50% to 80% margins
        }

        # Act
        validation = plan_generator.validate_business_assumptions(edge_case_data)

        # Assert
        assert not validation.assumptions_realistic
        assert len(validation.warning_flags) >= 3

        # Should flag unrealistic market share
        market_warning = next((w for w in validation.warning_flags if "market share" in w.description.lower()), None)
        assert market_warning is not None
        assert market_warning.severity == "High"
