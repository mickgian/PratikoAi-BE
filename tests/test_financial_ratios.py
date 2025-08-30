"""
TDD Tests for Financial Ratios Calculator.

This module tests comprehensive financial ratio calculations including liquidity,
profitability, efficiency, leverage ratios and financial health analysis.
"""

import pytest
from decimal import Decimal
from datetime import date
from typing import Dict, List, Optional

# These imports will fail initially - that's the TDD approach
from app.services.validators.financial_ratios import (
    FinancialRatiosCalculator,
    FinancialStatement,
    RatioResult,
    RatioCategory,
    LiquidityRatios,
    ProfitabilityRatios,
    EfficiencyRatios,
    LeverageRatios,
    MarketRatios,
    FinancialHealthScore,
    RatioBenchmark,
    Industry,
    TrendAnalysis,
    RatioInterpretation
)


class TestFinancialRatiosCalculator:
    """Test suite for Financial Ratios Calculator using TDD methodology."""
    
    @pytest.fixture
    def calculator(self):
        """Create financial ratios calculator instance for tests."""
        return FinancialRatiosCalculator()
    
    @pytest.fixture
    def sample_financial_data(self):
        """Sample financial statement data for testing."""
        return {
            'balance_sheet': {
                'current_assets': Decimal('500000'),
                'cash': Decimal('100000'),
                'inventory': Decimal('150000'),
                'accounts_receivable': Decimal('200000'),
                'total_assets': Decimal('2000000'),
                'current_liabilities': Decimal('300000'),
                'total_liabilities': Decimal('800000'),
                'shareholders_equity': Decimal('1200000'),
                'long_term_debt': Decimal('500000')
            },
            'income_statement': {
                'revenue': Decimal('3000000'),
                'cost_of_goods_sold': Decimal('1800000'),
                'gross_profit': Decimal('1200000'),
                'operating_expenses': Decimal('800000'),
                'operating_income': Decimal('400000'),
                'interest_expense': Decimal('30000'),
                'net_income': Decimal('280800'),  # After 24% tax
                'ebitda': Decimal('450000')
            },
            'market_data': {
                'shares_outstanding': Decimal('100000'),
                'market_price_per_share': Decimal('15.00'),
                'dividend_per_share': Decimal('1.50')
            }
        }
    
    # =========================================================================
    # Liquidity Ratios Tests
    # =========================================================================
    
    def test_current_ratio_calculation(self, calculator, sample_financial_data):
        """Test current ratio calculation and interpretation."""
        # Arrange
        balance_sheet = sample_financial_data['balance_sheet']
        expected_current_ratio = Decimal('500000') / Decimal('300000')  # 1.67
        
        # Act
        liquidity_ratios = calculator.calculate_liquidity_ratios(balance_sheet)
        
        # Assert
        assert isinstance(liquidity_ratios, LiquidityRatios)
        assert liquidity_ratios.current_ratio == expected_current_ratio
        assert abs(liquidity_ratios.current_ratio - Decimal('1.67')) < Decimal('0.01')
        assert liquidity_ratios.current_ratio_interpretation == "Good"  # Above 1.5 is good
        assert liquidity_ratios.current_ratio_formula == "Current Assets ÷ Current Liabilities = €500,000 ÷ €300,000 = 1.67"
    
    def test_quick_ratio_acid_test(self, calculator, sample_financial_data):
        """Test quick ratio (acid test) calculation."""
        # Arrange
        balance_sheet = sample_financial_data['balance_sheet']
        # Quick Assets = Current Assets - Inventory = 500,000 - 150,000 = 350,000
        # Quick Ratio = 350,000 / 300,000 = 1.17
        expected_quick_ratio = Decimal('1.17')
        
        # Act
        liquidity_ratios = calculator.calculate_liquidity_ratios(balance_sheet)
        
        # Assert
        assert abs(liquidity_ratios.quick_ratio - expected_quick_ratio) < Decimal('0.01')
        assert liquidity_ratios.quick_ratio_interpretation == "Adequate"  # Above 1.0 is adequate
        assert 'excludes inventory' in liquidity_ratios.quick_ratio_formula.lower()
    
    def test_cash_ratio_calculation(self, calculator, sample_financial_data):
        """Test cash ratio calculation."""
        # Arrange
        balance_sheet = sample_financial_data['balance_sheet']
        # Cash Ratio = Cash ÷ Current Liabilities = 100,000 / 300,000 = 0.33
        expected_cash_ratio = Decimal('0.33')
        
        # Act
        liquidity_ratios = calculator.calculate_liquidity_ratios(balance_sheet)
        
        # Assert
        assert abs(liquidity_ratios.cash_ratio - expected_cash_ratio) < Decimal('0.01')
        assert liquidity_ratios.cash_ratio_interpretation == "Low"  # Below 0.5 is low
    
    def test_working_capital_calculation(self, calculator, sample_financial_data):
        """Test working capital calculation and ratio."""
        # Arrange
        balance_sheet = sample_financial_data['balance_sheet']
        # Working Capital = Current Assets - Current Liabilities = 500,000 - 300,000 = 200,000
        expected_working_capital = Decimal('200000')
        
        # Act
        liquidity_ratios = calculator.calculate_liquidity_ratios(balance_sheet)
        
        # Assert
        assert liquidity_ratios.working_capital == expected_working_capital
        assert liquidity_ratios.working_capital > Decimal('0')  # Positive is good
        assert liquidity_ratios.working_capital_interpretation == "Healthy"
    
    # =========================================================================
    # Profitability Ratios Tests
    # =========================================================================
    
    def test_gross_profit_margin_calculation(self, calculator, sample_financial_data):
        """Test gross profit margin calculation."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        # Gross Profit Margin = (Revenue - COGS) / Revenue = 1,200,000 / 3,000,000 = 40%
        expected_gross_margin = Decimal('0.40')
        
        # Act
        profitability_ratios = calculator.calculate_profitability_ratios(
            income_statement, 
            sample_financial_data['balance_sheet']
        )
        
        # Assert
        assert isinstance(profitability_ratios, ProfitabilityRatios)
        assert profitability_ratios.gross_profit_margin == expected_gross_margin
        assert profitability_ratios.gross_profit_margin_percentage == Decimal('40.00')
        assert profitability_ratios.gross_profit_interpretation == "Good"  # 40% is good
    
    def test_operating_profit_margin_calculation(self, calculator, sample_financial_data):
        """Test operating profit margin calculation."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        # Operating Margin = Operating Income / Revenue = 400,000 / 3,000,000 = 13.33%
        expected_operating_margin = Decimal('0.1333')
        
        # Act
        profitability_ratios = calculator.calculate_profitability_ratios(
            income_statement, 
            sample_financial_data['balance_sheet']
        )
        
        # Assert
        assert abs(profitability_ratios.operating_profit_margin - expected_operating_margin) < Decimal('0.01')
        assert abs(profitability_ratios.operating_profit_margin_percentage - Decimal('13.33')) < Decimal('0.1')
        assert profitability_ratios.operating_profit_interpretation == "Good"  # Above 10% is good
    
    def test_net_profit_margin_calculation(self, calculator, sample_financial_data):
        """Test net profit margin calculation."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        # Net Margin = Net Income / Revenue = 280,800 / 3,000,000 = 9.36%
        expected_net_margin = Decimal('0.0936')
        
        # Act
        profitability_ratios = calculator.calculate_profitability_ratios(
            income_statement, 
            sample_financial_data['balance_sheet']
        )
        
        # Assert
        assert abs(profitability_ratios.net_profit_margin - expected_net_margin) < Decimal('0.01')
        assert abs(profitability_ratios.net_profit_margin_percentage - Decimal('9.36')) < Decimal('0.1')
        assert profitability_ratios.net_profit_interpretation == "Good"  # Above 5% is good
    
    def test_return_on_assets_roa_calculation(self, calculator, sample_financial_data):
        """Test Return on Assets (ROA) calculation."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        balance_sheet = sample_financial_data['balance_sheet']
        # ROA = Net Income / Total Assets = 280,800 / 2,000,000 = 14.04%
        expected_roa = Decimal('0.1404')
        
        # Act
        profitability_ratios = calculator.calculate_profitability_ratios(income_statement, balance_sheet)
        
        # Assert
        assert abs(profitability_ratios.return_on_assets - expected_roa) < Decimal('0.01')
        assert profitability_ratios.roa_interpretation == "Excellent"  # Above 10% is excellent
    
    def test_return_on_equity_roe_calculation(self, calculator, sample_financial_data):
        """Test Return on Equity (ROE) calculation."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        balance_sheet = sample_financial_data['balance_sheet']
        # ROE = Net Income / Shareholders Equity = 280,800 / 1,200,000 = 23.40%
        expected_roe = Decimal('0.234')
        
        # Act
        profitability_ratios = calculator.calculate_profitability_ratios(income_statement, balance_sheet)
        
        # Assert
        assert abs(profitability_ratios.return_on_equity - expected_roe) < Decimal('0.01')
        assert profitability_ratios.roe_interpretation == "Excellent"  # Above 15% is excellent
    
    # =========================================================================
    # Efficiency (Activity) Ratios Tests
    # =========================================================================
    
    def test_inventory_turnover_ratio(self, calculator, sample_financial_data):
        """Test inventory turnover ratio calculation."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        balance_sheet = sample_financial_data['balance_sheet']
        # Inventory Turnover = COGS / Inventory = 1,800,000 / 150,000 = 12.0
        expected_inventory_turnover = Decimal('12.0')
        
        # Act
        efficiency_ratios = calculator.calculate_efficiency_ratios(income_statement, balance_sheet)
        
        # Assert
        assert isinstance(efficiency_ratios, EfficiencyRatios)
        assert efficiency_ratios.inventory_turnover == expected_inventory_turnover
        assert efficiency_ratios.inventory_days == Decimal('30.42')  # 365/12 ≈ 30.4 days
        assert efficiency_ratios.inventory_turnover_interpretation == "Excellent"  # Above 8 is excellent
    
    def test_receivables_turnover_ratio(self, calculator, sample_financial_data):
        """Test accounts receivable turnover ratio calculation."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        balance_sheet = sample_financial_data['balance_sheet']
        # Receivables Turnover = Revenue / Accounts Receivable = 3,000,000 / 200,000 = 15.0
        expected_receivables_turnover = Decimal('15.0')
        
        # Act
        efficiency_ratios = calculator.calculate_efficiency_ratios(income_statement, balance_sheet)
        
        # Assert
        assert efficiency_ratios.receivables_turnover == expected_receivables_turnover
        assert efficiency_ratios.collection_period == Decimal('24.33')  # 365/15 ≈ 24.3 days
        assert efficiency_ratios.receivables_turnover_interpretation == "Excellent"  # Above 12 is excellent
    
    def test_asset_turnover_ratio(self, calculator, sample_financial_data):
        """Test total asset turnover ratio calculation."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        balance_sheet = sample_financial_data['balance_sheet']
        # Asset Turnover = Revenue / Total Assets = 3,000,000 / 2,000,000 = 1.50
        expected_asset_turnover = Decimal('1.50')
        
        # Act
        efficiency_ratios = calculator.calculate_efficiency_ratios(income_statement, balance_sheet)
        
        # Assert
        assert efficiency_ratios.asset_turnover == expected_asset_turnover
        assert efficiency_ratios.asset_turnover_interpretation == "Good"  # Above 1.0 is good
    
    def test_working_capital_turnover(self, calculator, sample_financial_data):
        """Test working capital turnover calculation."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        balance_sheet = sample_financial_data['balance_sheet']
        # Working Capital = Current Assets - Current Liabilities = 200,000
        # WC Turnover = Revenue / Working Capital = 3,000,000 / 200,000 = 15.0
        expected_wc_turnover = Decimal('15.0')
        
        # Act
        efficiency_ratios = calculator.calculate_efficiency_ratios(income_statement, balance_sheet)
        
        # Assert
        assert efficiency_ratios.working_capital_turnover == expected_wc_turnover
        assert efficiency_ratios.wc_turnover_interpretation == "Excellent"  # Above 10 is excellent
    
    # =========================================================================
    # Leverage (Solvency) Ratios Tests
    # =========================================================================
    
    def test_debt_to_equity_ratio(self, calculator, sample_financial_data):
        """Test debt-to-equity ratio calculation."""
        # Arrange
        balance_sheet = sample_financial_data['balance_sheet']
        # Debt-to-Equity = Total Liabilities / Shareholders Equity = 800,000 / 1,200,000 = 0.67
        expected_debt_to_equity = Decimal('0.67')
        
        # Act
        leverage_ratios = calculator.calculate_leverage_ratios(
            sample_financial_data['balance_sheet'],
            sample_financial_data['income_statement']
        )
        
        # Assert
        assert isinstance(leverage_ratios, LeverageRatios)
        assert abs(leverage_ratios.debt_to_equity - expected_debt_to_equity) < Decimal('0.01')
        assert leverage_ratios.debt_to_equity_interpretation == "Moderate"  # 0.5-1.0 is moderate
    
    def test_debt_ratio_calculation(self, calculator, sample_financial_data):
        """Test debt ratio calculation."""
        # Arrange
        balance_sheet = sample_financial_data['balance_sheet']
        # Debt Ratio = Total Liabilities / Total Assets = 800,000 / 2,000,000 = 0.40
        expected_debt_ratio = Decimal('0.40')
        
        # Act
        leverage_ratios = calculator.calculate_leverage_ratios(
            sample_financial_data['balance_sheet'],
            sample_financial_data['income_statement']
        )
        
        # Assert
        assert leverage_ratios.debt_ratio == expected_debt_ratio
        assert leverage_ratios.debt_ratio_percentage == Decimal('40.00')
        assert leverage_ratios.debt_ratio_interpretation == "Conservative"  # Below 50% is conservative
    
    def test_times_interest_earned_ratio(self, calculator, sample_financial_data):
        """Test times interest earned (interest coverage) ratio."""
        # Arrange
        income_statement = sample_financial_data['income_statement']
        # Times Interest Earned = Operating Income / Interest Expense = 400,000 / 30,000 = 13.33
        expected_tie = Decimal('13.33')
        
        # Act
        leverage_ratios = calculator.calculate_leverage_ratios(
            sample_financial_data['balance_sheet'],
            sample_financial_data['income_statement']
        )
        
        # Assert
        assert abs(leverage_ratios.times_interest_earned - expected_tie) < Decimal('0.1')
        assert leverage_ratios.tie_interpretation == "Strong"  # Above 10 is strong
    
    def test_equity_multiplier_calculation(self, calculator, sample_financial_data):
        """Test equity multiplier calculation."""
        # Arrange
        balance_sheet = sample_financial_data['balance_sheet']
        # Equity Multiplier = Total Assets / Shareholders Equity = 2,000,000 / 1,200,000 = 1.67
        expected_equity_multiplier = Decimal('1.67')
        
        # Act
        leverage_ratios = calculator.calculate_leverage_ratios(
            sample_financial_data['balance_sheet'],
            sample_financial_data['income_statement']
        )
        
        # Assert
        assert abs(leverage_ratios.equity_multiplier - expected_equity_multiplier) < Decimal('0.01')
        assert leverage_ratios.equity_multiplier_interpretation == "Conservative"  # Below 2.0 is conservative
    
    # =========================================================================
    # Market Ratios Tests
    # =========================================================================
    
    def test_price_to_earnings_pe_ratio(self, calculator, sample_financial_data):
        """Test Price-to-Earnings (P/E) ratio calculation."""
        # Arrange
        market_data = sample_financial_data['market_data']
        income_statement = sample_financial_data['income_statement']
        # EPS = Net Income / Shares Outstanding = 280,800 / 100,000 = 2.808
        # P/E = Market Price / EPS = 15.00 / 2.808 = 5.34
        expected_pe_ratio = Decimal('5.34')
        
        # Act
        market_ratios = calculator.calculate_market_ratios(
            market_data, 
            income_statement, 
            sample_financial_data['balance_sheet']
        )
        
        # Assert
        assert isinstance(market_ratios, MarketRatios)
        assert abs(market_ratios.pe_ratio - expected_pe_ratio) < Decimal('0.1')
        assert market_ratios.earnings_per_share == Decimal('2.808')
        assert market_ratios.pe_ratio_interpretation == "Undervalued"  # Below 15 often undervalued
    
    def test_price_to_book_pb_ratio(self, calculator, sample_financial_data):
        """Test Price-to-Book (P/B) ratio calculation."""
        # Arrange
        market_data = sample_financial_data['market_data']
        balance_sheet = sample_financial_data['balance_sheet']
        # Book Value per Share = Shareholders Equity / Shares = 1,200,000 / 100,000 = 12.00
        # P/B = Market Price / Book Value per Share = 15.00 / 12.00 = 1.25
        expected_pb_ratio = Decimal('1.25')
        
        # Act
        market_ratios = calculator.calculate_market_ratios(
            market_data, 
            sample_financial_data['income_statement'], 
            balance_sheet
        )
        
        # Assert
        assert market_ratios.pb_ratio == expected_pb_ratio
        assert market_ratios.book_value_per_share == Decimal('12.00')
        assert market_ratios.pb_ratio_interpretation == "Fair Value"  # Around 1.0-1.5 is fair
    
    def test_dividend_yield_calculation(self, calculator, sample_financial_data):
        """Test dividend yield calculation."""
        # Arrange
        market_data = sample_financial_data['market_data']
        # Dividend Yield = Dividend per Share / Market Price = 1.50 / 15.00 = 0.10 (10%)
        expected_dividend_yield = Decimal('0.10')
        
        # Act
        market_ratios = calculator.calculate_market_ratios(
            market_data, 
            sample_financial_data['income_statement'], 
            sample_financial_data['balance_sheet']
        )
        
        # Assert
        assert market_ratios.dividend_yield == expected_dividend_yield
        assert market_ratios.dividend_yield_percentage == Decimal('10.00')
        assert market_ratios.dividend_yield_interpretation == "High"  # Above 6% is high
    
    def test_market_capitalization_calculation(self, calculator, sample_financial_data):
        """Test market capitalization calculation."""
        # Arrange
        market_data = sample_financial_data['market_data']
        # Market Cap = Shares Outstanding × Market Price = 100,000 × 15.00 = 1,500,000
        expected_market_cap = Decimal('1500000')
        
        # Act
        market_ratios = calculator.calculate_market_ratios(
            market_data, 
            sample_financial_data['income_statement'], 
            sample_financial_data['balance_sheet']
        )
        
        # Assert
        assert market_ratios.market_capitalization == expected_market_cap
        assert market_ratios.market_cap_classification == "Small Cap"  # Below €2B
    
    # =========================================================================
    # Comprehensive Financial Health Analysis
    # =========================================================================
    
    def test_comprehensive_financial_health_score(self, calculator, sample_financial_data):
        """Test comprehensive financial health score calculation."""
        # Act
        health_score = calculator.calculate_financial_health_score(sample_financial_data)
        
        # Assert
        assert isinstance(health_score, FinancialHealthScore)
        assert Decimal('0') <= health_score.overall_score <= Decimal('100')
        assert len(health_score.category_scores) == 5  # Liquidity, Profitability, Efficiency, Leverage, Market
        
        # Each category should have a score
        assert 'liquidity' in health_score.category_scores
        assert 'profitability' in health_score.category_scores  
        assert 'efficiency' in health_score.category_scores
        assert 'leverage' in health_score.category_scores
        assert 'market' in health_score.category_scores
        
        # Should provide interpretation
        assert health_score.health_interpretation in ['Excellent', 'Good', 'Fair', 'Poor', 'Critical']
        assert len(health_score.key_strengths) >= 1
        assert len(health_score.areas_for_improvement) >= 1
    
    def test_ratio_benchmarking_industry_comparison(self, calculator, sample_financial_data):
        """Test ratio benchmarking against industry averages."""
        # Arrange
        industry = Industry.MANUFACTURING
        
        # Act
        benchmark_analysis = calculator.benchmark_against_industry(
            financial_data=sample_financial_data,
            industry=industry
        )
        
        # Assert
        assert isinstance(benchmark_analysis, RatioBenchmark)
        assert benchmark_analysis.industry == industry
        assert len(benchmark_analysis.ratio_comparisons) >= 10
        
        # Should compare key ratios
        current_ratio_comparison = next((c for c in benchmark_analysis.ratio_comparisons 
                                       if c.ratio_name == 'current_ratio'), None)
        assert current_ratio_comparison is not None
        assert current_ratio_comparison.company_value > Decimal('0')
        assert current_ratio_comparison.industry_median > Decimal('0')
        assert current_ratio_comparison.percentile_rank >= Decimal('0')
        assert current_ratio_comparison.performance in ['Above Average', 'Average', 'Below Average']
    
    def test_trend_analysis_multi_period(self, calculator):
        """Test trend analysis with multiple periods of financial data."""
        # Arrange
        multi_period_data = {
            '2022': {
                'revenue': Decimal('2500000'),
                'net_income': Decimal('200000'),
                'total_assets': Decimal('1800000'),
                'current_ratio': Decimal('1.50')
            },
            '2023': {
                'revenue': Decimal('2750000'),
                'net_income': Decimal('240000'),
                'total_assets': Decimal('1900000'),
                'current_ratio': Decimal('1.60')
            },
            '2024': {
                'revenue': Decimal('3000000'),
                'net_income': Decimal('280800'),
                'total_assets': Decimal('2000000'),
                'current_ratio': Decimal('1.67')
            }
        }
        
        # Act
        trend_analysis = calculator.analyze_financial_trends(multi_period_data)
        
        # Assert
        assert isinstance(trend_analysis, TrendAnalysis)
        assert len(trend_analysis.periods) == 3
        assert trend_analysis.analysis_period == '2022-2024'
        
        # Revenue trend should be positive
        revenue_trend = trend_analysis.metric_trends['revenue']
        assert revenue_trend.direction == 'Increasing'
        assert revenue_trend.compound_annual_growth_rate > Decimal('0')
        assert revenue_trend.trend_strength == 'Strong'  # Consistent growth
        
        # Current ratio trend should be improving
        current_ratio_trend = trend_analysis.metric_trends['current_ratio'] 
        assert current_ratio_trend.direction == 'Improving'
    
    # =========================================================================
    # Specialized Industry Analysis
    # =========================================================================
    
    def test_retail_industry_specialized_ratios(self, calculator, sample_financial_data):
        """Test specialized ratios for retail industry."""
        # Arrange
        retail_data = sample_financial_data.copy()
        retail_data['industry_specific'] = {
            'same_store_sales_growth': Decimal('0.08'),  # 8% same-store growth
            'inventory_shrinkage': Decimal('0.02'),      # 2% shrinkage
            'sales_per_square_foot': Decimal('500'),     # €500 per sq ft
            'customer_traffic': Decimal('10000'),        # Monthly customers
            'average_transaction_value': Decimal('25')    # €25 average purchase
        }
        
        # Act
        retail_ratios = calculator.calculate_industry_specific_ratios(
            financial_data=retail_data,
            industry=Industry.RETAIL
        )
        
        # Assert
        assert 'inventory_turnover' in retail_ratios.key_metrics
        assert 'sales_per_square_foot' in retail_ratios.key_metrics
        assert 'same_store_sales_growth' in retail_ratios.key_metrics
        assert retail_ratios.industry_score >= Decimal('0')
        assert retail_ratios.competitive_position in ['Leader', 'Above Average', 'Average', 'Below Average', 'Laggard']
    
    def test_saas_industry_specialized_ratios(self, calculator, sample_financial_data):
        """Test specialized ratios for SaaS industry."""
        # Arrange
        saas_data = sample_financial_data.copy()
        saas_data['industry_specific'] = {
            'monthly_recurring_revenue': Decimal('250000'),  # €250K MRR
            'customer_acquisition_cost': Decimal('500'),     # €500 CAC
            'lifetime_value': Decimal('3000'),               # €3K LTV
            'churn_rate': Decimal('0.05'),                   # 5% monthly churn
            'gross_revenue_retention': Decimal('0.95'),      # 95% GRR
            'net_revenue_retention': Decimal('1.10')         # 110% NRR (expansion)
        }
        
        # Act
        saas_ratios = calculator.calculate_industry_specific_ratios(
            financial_data=saas_data,
            industry=Industry.SAAS
        )
        
        # Assert
        assert 'ltv_cac_ratio' in saas_ratios.key_metrics
        assert saas_ratios.key_metrics['ltv_cac_ratio'] == Decimal('6.0')  # 3000/500
        assert saas_ratios.key_metrics['ltv_cac_ratio'] >= Decimal('3')    # Healthy SaaS ratio
        assert 'monthly_churn_rate' in saas_ratios.key_metrics
        assert 'net_revenue_retention' in saas_ratios.key_metrics
    
    # =========================================================================
    # Performance and Edge Case Tests
    # =========================================================================
    
    def test_ratio_calculation_performance(self, calculator, sample_financial_data):
        """Test ratio calculation performance with complex datasets."""
        import time
        
        # Arrange - Large dataset simulation
        large_dataset = sample_financial_data.copy()
        for i in range(100):  # Simulate 100 periods of data
            large_dataset[f'period_{i}'] = sample_financial_data['income_statement'].copy()
        
        # Act
        start_time = time.time()
        all_ratios = calculator.calculate_comprehensive_ratios(large_dataset)
        end_time = time.time()
        
        # Assert
        calculation_time = end_time - start_time
        assert calculation_time < 5.0  # Should complete in under 5 seconds
        assert len(all_ratios.categories) >= 5
        assert all_ratios.calculation_metadata.processing_time < 5000  # milliseconds
    
    def test_ratio_calculation_edge_cases(self, calculator):
        """Test ratio calculations with edge cases and zero values."""
        # Arrange - Edge case data
        edge_case_data = {
            'balance_sheet': {
                'current_assets': Decimal('0'),      # Zero current assets
                'current_liabilities': Decimal('100000'),
                'total_assets': Decimal('500000'),
                'shareholders_equity': Decimal('0'), # Zero equity (debt-financed)
                'inventory': Decimal('0')            # No inventory
            },
            'income_statement': {
                'revenue': Decimal('1000000'),
                'cost_of_goods_sold': Decimal('0'),  # No COGS
                'net_income': Decimal('-50000'),     # Net loss
                'interest_expense': Decimal('0')     # No interest expense
            }
        }
        
        # Act & Assert - Should handle edge cases gracefully
        liquidity_ratios = calculator.calculate_liquidity_ratios(edge_case_data['balance_sheet'])
        
        # Zero current assets should result in zero current ratio
        assert liquidity_ratios.current_ratio == Decimal('0')
        assert liquidity_ratios.current_ratio_interpretation == "Critical"
        
        # Should handle division by zero gracefully
        assert liquidity_ratios.inventory_turnover is None or liquidity_ratios.inventory_turnover == float('inf')
    
    def test_ratio_interpretation_accuracy(self, calculator, sample_financial_data):
        """Test accuracy of ratio interpretations across different ranges."""
        # Arrange - Test various ratio ranges
        test_cases = [
            {'current_ratio': Decimal('0.5'), 'expected': 'Poor'},
            {'current_ratio': Decimal('1.5'), 'expected': 'Good'},
            {'current_ratio': Decimal('3.0'), 'expected': 'Excellent'},
            {'roe': Decimal('0.05'), 'expected': 'Poor'},     # 5%
            {'roe': Decimal('0.15'), 'expected': 'Good'},     # 15%
            {'roe': Decimal('0.25'), 'expected': 'Excellent'} # 25%
        ]
        
        # Act & Assert
        for case in test_cases:
            if 'current_ratio' in case:
                interpretation = calculator.interpret_current_ratio(case['current_ratio'])
                assert interpretation == case['expected']
            elif 'roe' in case:
                interpretation = calculator.interpret_roe(case['roe'])
                assert interpretation == case['expected']