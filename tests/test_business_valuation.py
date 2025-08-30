"""
TDD Tests for Business Valuation Engine.

This module tests business valuation methods including DCF, EBITDA multiples,
asset-based valuation, and working capital calculations.
"""

import pytest
from decimal import Decimal
from datetime import date
from typing import Dict, List

# These imports will fail initially - that's the TDD approach
from app.services.validators.business_valuation import (
    BusinessValuationEngine,
    DCFValuation,
    EBITDAValuation,
    AssetBasedValuation,
    ValuationResult,
    CashFlowProjection,
    TerminalValue,
    Industry,
    ValuationMethod
)


class TestBusinessValuationEngine:
    """Test suite for Business Valuation Engine using TDD methodology."""
    
    @pytest.fixture
    def valuation_engine(self):
        """Create valuation engine instance for tests."""
        return BusinessValuationEngine()
    
    # =========================================================================
    # DCF (Discounted Cash Flow) Tests
    # =========================================================================
    
    def test_dcf_valuation_5_year_projection(self, valuation_engine):
        """Test DCF valuation with 5-year cash flow projections."""
        # Arrange
        cash_flows = [
            Decimal('100000'),  # Year 1
            Decimal('120000'),  # Year 2 (+20% growth)
            Decimal('144000'),  # Year 3 (+20% growth)
            Decimal('172800'),  # Year 4 (+20% growth)
            Decimal('207360'),  # Year 5 (+20% growth)
        ]
        discount_rate = Decimal('0.10')  # 10% WACC
        terminal_growth_rate = Decimal('0.03')  # 3% perpetual growth
        
        # Expected calculations:
        # Terminal Value = Year 5 CF * (1 + terminal_growth) / (discount_rate - terminal_growth)
        # Terminal Value = 207,360 * 1.03 / (0.10 - 0.03) = 213,660.8 / 0.07 = 3,052,297
        # PV of Terminal Value = 3,052,297 / (1.10)^5 = 1,895,126
        # PV of Cash Flows = 100K/1.1 + 120K/1.1^2 + 144K/1.1^3 + 172.8K/1.1^4 + 207.36K/1.1^5
        #                  = 90,909 + 99,174 + 108,243 + 118,068 + 128,724 = 545,118
        # Enterprise Value = 545,118 + 1,895,126 = 2,440,244
        expected_enterprise_value = Decimal('2440244')
        
        # Act
        result = valuation_engine.calculate_dcf_valuation(
            cash_flows=cash_flows,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate
        )
        
        # Assert
        assert isinstance(result, DCFValuation)
        assert result.enterprise_value == expected_enterprise_value
        assert result.terminal_value > Decimal('3000000')
        assert result.discount_rate == discount_rate
        assert len(result.pv_cash_flows) == 5
        assert result.formula.startswith("DCF Valuation:")
        assert result.confidence_score >= Decimal('0.8')  # High confidence for standard DCF
    
    def test_dcf_with_debt_to_equity_value(self, valuation_engine):
        """Test DCF calculation converting enterprise value to equity value."""
        # Arrange
        cash_flows = [Decimal('50000')] * 5  # Stable cash flows
        discount_rate = Decimal('0.08')
        terminal_growth_rate = Decimal('0.02')
        net_debt = Decimal('200000')  # Company has debt
        cash = Decimal('50000')      # Company has cash
        
        # Act
        result = valuation_engine.calculate_dcf_valuation(
            cash_flows=cash_flows,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate,
            net_debt=net_debt,
            cash_position=cash
        )
        
        # Assert
        assert result.equity_value == result.enterprise_value - net_debt + cash
        assert result.net_debt == net_debt
        assert result.cash_position == cash
        assert 'Enterprise Value to Equity Bridge' in result.formula
    
    def test_dcf_sensitivity_analysis(self, valuation_engine):
        """Test DCF sensitivity analysis with different discount rates."""
        # Arrange
        cash_flows = [Decimal('100000')] * 5
        base_discount_rate = Decimal('0.10')
        discount_rate_scenarios = [
            Decimal('0.08'),   # -2%
            Decimal('0.10'),   # Base case
            Decimal('0.12'),   # +2%
        ]
        
        # Act
        results = valuation_engine.dcf_sensitivity_analysis(
            cash_flows=cash_flows,
            base_discount_rate=base_discount_rate,
            discount_rate_range=discount_rate_scenarios,
            terminal_growth_rate=Decimal('0.03')
        )
        
        # Assert
        assert len(results) == 3
        assert results[0]['enterprise_value'] > results[1]['enterprise_value']  # Lower rate = higher value
        assert results[1]['enterprise_value'] > results[2]['enterprise_value']  # Higher rate = lower value
        assert all('sensitivity' in r for r in results)
    
    # =========================================================================
    # EBITDA Multiple Valuation Tests
    # =========================================================================
    
    def test_ebitda_multiple_valuation_technology(self, valuation_engine):
        """Test EBITDA multiple valuation for technology company."""
        # Arrange
        ebitda = Decimal('500000')
        industry = Industry.TECHNOLOGY
        expected_multiple_range = (Decimal('12'), Decimal('18'))  # Tech multiples
        expected_valuation_low = ebitda * expected_multiple_range[0]
        expected_valuation_high = ebitda * expected_multiple_range[1]
        
        # Act
        result = valuation_engine.calculate_ebitda_valuation(
            ebitda=ebitda,
            industry=industry,
            company_size='mid_cap'
        )
        
        # Assert
        assert isinstance(result, EBITDAValuation)
        assert result.ebitda == ebitda
        assert result.industry == industry
        assert result.valuation_low >= expected_valuation_low
        assert result.valuation_high <= expected_valuation_high
        assert expected_valuation_low <= result.fair_value <= expected_valuation_high
        assert len(result.comparable_multiples) >= 3
        assert result.confidence_score >= Decimal('0.7')
    
    def test_ebitda_multiple_valuation_manufacturing(self, valuation_engine):
        """Test EBITDA multiple valuation for manufacturing company."""
        # Arrange
        ebitda = Decimal('1000000')
        industry = Industry.MANUFACTURING
        expected_multiple_range = (Decimal('6'), Decimal('12'))  # Manufacturing multiples
        
        # Act
        result = valuation_engine.calculate_ebitda_valuation(
            ebitda=ebitda,
            industry=industry,
            company_size='large_cap'
        )
        
        # Assert
        assert result.industry == industry
        assert result.multiple_applied >= expected_multiple_range[0]
        assert result.multiple_applied <= expected_multiple_range[1]
        assert result.formula.includes(f"{industry.value} industry")
    
    def test_ebitda_multiple_with_adjustments(self, valuation_engine):
        """Test EBITDA multiple valuation with company-specific adjustments."""
        # Arrange
        ebitda = Decimal('750000')
        industry = Industry.RETAIL
        adjustments = {
            'growth_premium': Decimal('1.2'),      # 20% premium for high growth
            'liquidity_discount': Decimal('0.9'),   # 10% discount for illiquidity
            'management_premium': Decimal('1.1')    # 10% premium for strong management
        }
        
        # Act
        result = valuation_engine.calculate_ebitda_valuation(
            ebitda=ebitda,
            industry=industry,
            adjustments=adjustments
        )
        
        # Assert
        assert result.adjustments == adjustments
        assert result.adjusted_multiple != result.base_multiple
        assert 'growth premium' in result.formula.lower()
        assert 'liquidity discount' in result.formula.lower()
        assert len(result.adjustment_explanations) == 3
    
    # =========================================================================
    # Asset-Based Valuation Tests  
    # =========================================================================
    
    def test_asset_based_valuation_book_value(self, valuation_engine):
        """Test asset-based valuation using book value approach."""
        # Arrange
        assets = {
            'current_assets': Decimal('500000'),
            'ppe': Decimal('1200000'),           # Property, plant, equipment
            'intangible_assets': Decimal('300000'),
            'investments': Decimal('200000')
        }
        liabilities = {
            'current_liabilities': Decimal('300000'),
            'long_term_debt': Decimal('800000'),
            'other_liabilities': Decimal('100000')
        }
        expected_book_value = Decimal('1000000')  # 2.2M assets - 1.2M liabilities
        
        # Act
        result = valuation_engine.calculate_asset_based_valuation(
            assets=assets,
            liabilities=liabilities,
            method='book_value'
        )
        
        # Assert
        assert isinstance(result, AssetBasedValuation)
        assert result.total_assets == sum(assets.values())
        assert result.total_liabilities == sum(liabilities.values())
        assert result.book_value == expected_book_value
        assert result.method == 'book_value'
        assert result.confidence_score >= Decimal('0.6')
    
    def test_asset_based_valuation_liquidation_value(self, valuation_engine):
        """Test asset-based valuation using liquidation value approach."""
        # Arrange
        assets = {
            'inventory': Decimal('400000'),
            'receivables': Decimal('200000'),
            'equipment': Decimal('600000'),
            'real_estate': Decimal('1000000')
        }
        liquidation_rates = {
            'inventory': Decimal('0.6'),      # 60% recovery
            'receivables': Decimal('0.9'),    # 90% recovery
            'equipment': Decimal('0.4'),      # 40% recovery
            'real_estate': Decimal('0.8')     # 80% recovery
        }
        expected_liquidation_value = (
            Decimal('400000') * Decimal('0.6') +  # 240,000
            Decimal('200000') * Decimal('0.9') +  # 180,000
            Decimal('600000') * Decimal('0.4') +  # 240,000
            Decimal('1000000') * Decimal('0.8')   # 800,000
        )  # Total: 1,460,000
        
        # Act
        result = valuation_engine.calculate_asset_based_valuation(
            assets=assets,
            liabilities={},
            method='liquidation_value',
            liquidation_rates=liquidation_rates
        )
        
        # Assert
        assert result.liquidation_value == expected_liquidation_value
        assert result.method == 'liquidation_value'
        assert len(result.asset_adjustments) == 4
        assert result.formula.includes("liquidation rates applied")
    
    # =========================================================================
    # Working Capital Calculations
    # =========================================================================
    
    def test_working_capital_calculation_basic(self, valuation_engine):
        """Test basic working capital calculation."""
        # Arrange
        current_assets = Decimal('800000')
        current_liabilities = Decimal('400000')
        expected_working_capital = Decimal('400000')
        
        # Act
        result = valuation_engine.calculate_working_capital(
            current_assets=current_assets,
            current_liabilities=current_liabilities
        )
        
        # Assert
        assert result.working_capital == expected_working_capital
        assert result.working_capital_ratio == Decimal('2.0')  # 800k / 400k
        assert result.formula == "Working Capital = €800,000 - €400,000 = €400,000"
    
    def test_working_capital_detailed_breakdown(self, valuation_engine):
        """Test detailed working capital calculation with components."""
        # Arrange
        current_assets = {
            'cash': Decimal('100000'),
            'receivables': Decimal('300000'),
            'inventory': Decimal('250000'),
            'prepaid_expenses': Decimal('50000')
        }
        current_liabilities = {
            'accounts_payable': Decimal('200000'),
            'accrued_expenses': Decimal('100000'),
            'short_term_debt': Decimal('80000')
        }
        
        # Act
        result = valuation_engine.calculate_working_capital(
            current_assets=current_assets,
            current_liabilities=current_liabilities,
            detailed=True
        )
        
        # Assert
        assert result.cash == current_assets['cash']
        assert result.receivables == current_assets['receivables'] 
        assert result.inventory == current_assets['inventory']
        assert result.accounts_payable == current_liabilities['accounts_payable']
        assert len(result.components) == 7  # 4 assets + 3 liabilities
        assert result.working_capital == Decimal('320000')  # 700k - 380k
    
    def test_working_capital_requirements_projection(self, valuation_engine):
        """Test working capital requirements for business growth."""
        # Arrange
        current_working_capital = Decimal('500000')
        revenue_growth_rates = [Decimal('0.2'), Decimal('0.15'), Decimal('0.10')]  # 20%, 15%, 10%
        working_capital_ratio = Decimal('0.15')  # 15% of revenue
        base_revenue = Decimal('2000000')
        
        # Act
        result = valuation_engine.project_working_capital_needs(
            base_revenue=base_revenue,
            current_working_capital=current_working_capital,
            growth_rates=revenue_growth_rates,
            wc_ratio=working_capital_ratio
        )
        
        # Assert
        assert len(result.projections) == 3
        assert result.projections[0]['working_capital'] > current_working_capital
        assert result.projections[0]['additional_funding'] > Decimal('0')
        assert result.total_additional_funding > Decimal('0')
        assert 'working capital investment' in result.summary.lower()
    
    # =========================================================================
    # Comprehensive Valuation Tests
    # =========================================================================
    
    def test_comprehensive_business_valuation_triangulation(self, valuation_engine):
        """Test comprehensive valuation using multiple methods for triangulation."""
        # Arrange
        company_data = {
            'cash_flows': [Decimal('200000')] * 5,
            'ebitda': Decimal('600000'),
            'assets': {'total': Decimal('2000000')},
            'liabilities': {'total': Decimal('800000')},
            'industry': Industry.TECHNOLOGY,
            'discount_rate': Decimal('0.12')
        }
        
        # Act
        result = valuation_engine.comprehensive_valuation(
            company_data=company_data,
            methods=[ValuationMethod.DCF, ValuationMethod.EBITDA_MULTIPLE, ValuationMethod.ASSET_BASED]
        )
        
        # Assert
        assert len(result.valuations) == 3
        assert 'dcf' in result.valuations
        assert 'ebitda_multiple' in result.valuations  
        assert 'asset_based' in result.valuations
        assert result.recommended_value > Decimal('0')
        assert result.valuation_range['low'] < result.recommended_value < result.valuation_range['high']
        assert result.methodology_weights['dcf'] >= Decimal('0.4')  # DCF should have high weight
        assert len(result.executive_summary) > 100  # Detailed summary
    
    # =========================================================================
    # Industry-Specific Valuation Tests
    # =========================================================================
    
    def test_saas_business_valuation_specialized(self, valuation_engine):
        """Test specialized SaaS business valuation with recurring revenue."""
        # Arrange
        saas_metrics = {
            'mrr': Decimal('50000'),                    # Monthly Recurring Revenue
            'arr': Decimal('600000'),                   # Annual Recurring Revenue
            'churn_rate': Decimal('0.05'),             # 5% monthly churn
            'cac': Decimal('200'),                      # Customer Acquisition Cost
            'ltv': Decimal('2000'),                     # Lifetime Value
            'growth_rate': Decimal('0.15')             # 15% monthly growth
        }
        
        # Act
        result = valuation_engine.value_saas_business(saas_metrics)
        
        # Assert
        assert result.revenue_multiple >= Decimal('8')   # SaaS typically 8-15x revenue
        assert result.ltv_cac_ratio == saas_metrics['ltv'] / saas_metrics['cac']
        assert result.ltv_cac_ratio >= Decimal('3')      # Healthy SaaS should be 3+
        assert 'recurring revenue premium' in result.valuation_factors
        assert result.growth_adjusted_value > result.base_value
    
    def test_ecommerce_business_valuation_specialized(self, valuation_engine):
        """Test specialized e-commerce business valuation."""
        # Arrange
        ecommerce_metrics = {
            'gross_revenue': Decimal('2000000'),
            'net_revenue': Decimal('1800000'),
            'gross_margin': Decimal('0.4'),            # 40% margin
            'inventory_turnover': Decimal('6'),        # 6x per year
            'customer_concentration': Decimal('0.15'), # 15% from top customer
            'marketplace_dependency': Decimal('0.6')   # 60% from marketplaces
        }
        
        # Act
        result = valuation_engine.value_ecommerce_business(ecommerce_metrics)
        
        # Assert
        assert result.revenue_multiple <= Decimal('4')  # E-commerce typically lower multiples
        assert 'inventory risk' in result.risk_factors
        assert 'marketplace dependency' in result.risk_factors
        assert result.diversification_score < Decimal('1.0')  # Penalty for concentration
    
    # =========================================================================
    # Performance and Edge Case Tests
    # =========================================================================
    
    def test_valuation_performance_complex_calculation(self, valuation_engine):
        """Test valuation performance with complex calculations."""
        import time
        
        # Arrange
        complex_data = {
            'cash_flows': [Decimal('100000') * (1 + i*0.1) for i in range(10)],  # 10 years
            'ebitda': Decimal('500000'),
            'assets': {f'asset_{i}': Decimal('100000') for i in range(20)},  # 20 asset types
            'industry': Industry.MANUFACTURING
        }
        
        # Act
        start_time = time.time()
        result = valuation_engine.comprehensive_valuation(complex_data)
        end_time = time.time()
        
        # Assert
        assert (end_time - start_time) < 2.0  # Should complete in < 2 seconds
        assert result.calculation_time < 2000  # Measured in milliseconds
        assert result.recommended_value > Decimal('0')
    
    def test_valuation_edge_case_negative_cash_flows(self, valuation_engine):
        """Test valuation with negative cash flows (startup scenario)."""
        # Arrange
        cash_flows = [
            Decimal('-100000'),  # Year 1 - losing money
            Decimal('-50000'),   # Year 2 - smaller loss
            Decimal('100000'),   # Year 3 - breakeven
            Decimal('300000'),   # Year 4 - profitable
            Decimal('500000')    # Year 5 - strong growth
        ]
        
        # Act
        result = valuation_engine.calculate_dcf_valuation(
            cash_flows=cash_flows,
            discount_rate=Decimal('0.15'),  # Higher rate for risk
            terminal_growth_rate=Decimal('0.03')
        )
        
        # Assert
        assert result.enterprise_value > Decimal('0')  # Should still have positive value
        assert result.confidence_score < Decimal('0.7')  # Lower confidence due to negative flows
        assert 'negative cash flows' in result.risk_factors
        assert len(result.scenario_analysis) >= 3  # Should provide scenarios
    
    def test_valuation_zero_terminal_value(self, valuation_engine):
        """Test DCF valuation with zero terminal value (mature declining business)."""
        # Arrange
        declining_cash_flows = [Decimal('500000') * (0.9 ** i) for i in range(5)]  # 10% annual decline
        
        # Act
        result = valuation_engine.calculate_dcf_valuation(
            cash_flows=declining_cash_flows,
            discount_rate=Decimal('0.10'),
            terminal_growth_rate=Decimal('0.0')  # No terminal growth
        )
        
        # Assert
        assert result.terminal_value == Decimal('0')
        assert result.enterprise_value == sum(result.pv_cash_flows)
        assert 'declining business' in result.business_assumptions.lower()
        assert result.confidence_score >= Decimal('0.8')  # High confidence in finite model