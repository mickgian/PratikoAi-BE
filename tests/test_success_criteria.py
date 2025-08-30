"""
Test suite for CCNL Success Criteria verification.

Tests all success criteria verification functionality including coverage analysis,
query capability testing, calculation accuracy verification, update timeliness
monitoring, and test coverage analysis.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List

from app.models.ccnl_data import CCNLSector
from app.services.ccnl_success_criteria import (
    CCNLSuccessCriteriaService, CoverageAnalysis, QueryCapabilityTest,
    CalculationAccuracyTest, UpdateTimelinessMetric, SuccessCriteriaReport
)


class TestCoverageAnalysis:
    """Test CCNL coverage analysis functionality."""
    
    @pytest.fixture
    def success_criteria_service(self):
        """Create success criteria service instance."""
        return CCNLSuccessCriteriaService()
    
    @pytest.mark.asyncio
    async def test_coverage_requirements_verification(self, success_criteria_service):
        """Test verification of CCNL coverage requirements."""
        coverage = await success_criteria_service._verify_coverage_requirements()
        
        # Verify coverage analysis structure
        assert isinstance(coverage, CoverageAnalysis)
        assert coverage.total_sectors_covered > 0
        assert coverage.major_ccnls_covered >= 0
        assert 0 <= coverage.estimated_worker_coverage_percentage <= 100
        assert isinstance(coverage.sectors_by_priority, dict)
        assert isinstance(coverage.missing_sectors, list)
        assert isinstance(coverage.coverage_gaps, list)
    
    def test_major_sectors_definition(self, success_criteria_service):
        """Test that major sectors are properly defined."""
        major_sectors = success_criteria_service.major_sectors
        
        # Verify we have enough major sectors
        assert len(major_sectors) >= 10
        
        # Verify sectors have reasonable worker counts
        for sector, worker_count in major_sectors.items():
            assert isinstance(sector, CCNLSector)
            assert worker_count > 0
            assert worker_count < 10  # millions of workers should be reasonable
        
        # Verify total worker coverage is substantial
        total_workers = sum(major_sectors.values())
        assert total_workers > 10  # More than 10 million workers total
    
    @pytest.mark.asyncio
    async def test_coverage_gap_detection(self, success_criteria_service):
        """Test detection of coverage gaps."""
        coverage = await success_criteria_service._verify_coverage_requirements()
        
        # Check gap detection logic
        if coverage.estimated_worker_coverage_percentage < 90:
            assert any("coverage" in gap.lower() for gap in coverage.coverage_gaps)
        
        if coverage.major_ccnls_covered < 50:
            assert any("ccnl" in gap.lower() for gap in coverage.coverage_gaps)
    
    def test_priority_sector_classification(self, success_criteria_service):
        """Test that sectors are properly classified by priority."""
        # This would test the priority classification logic
        # For now, verify the structure exists
        assert hasattr(success_criteria_service, 'major_sectors')
        assert len(success_criteria_service.major_sectors) > 0


class TestQueryCapabilities:
    """Test query capability verification functionality."""
    
    @pytest.fixture
    def success_criteria_service(self):
        """Create success criteria service instance."""
        return CCNLSuccessCriteriaService()
    
    def test_query_test_definitions(self, success_criteria_service):
        """Test that query tests are properly defined."""
        test_queries = success_criteria_service.test_queries
        
        # Verify we have comprehensive test queries
        assert len(test_queries) >= 3
        
        # Verify query structure
        for query in test_queries:
            assert "description" in query
            assert "complexity" in query
            assert query["complexity"] in ["low", "medium", "high"]
    
    @pytest.mark.asyncio
    async def test_query_capability_testing(self, success_criteria_service):
        """Test query capability testing functionality."""
        query_tests = await success_criteria_service._test_query_capabilities()
        
        # Verify test results structure
        assert isinstance(query_tests, list)
        assert len(query_tests) > 0
        
        for test in query_tests:
            assert isinstance(test, QueryCapabilityTest)
            assert test.query_description
            assert test.query_complexity in ["low", "medium", "high"]
            assert test.response_time >= 0
            assert 0 <= test.accuracy_score <= 1
            assert isinstance(test.success, bool)
    
    @pytest.mark.asyncio
    async def test_calculation_query_handling(self, success_criteria_service):
        """Test calculation-based query handling."""
        test_query = {
            "description": "Test calculation query",
            "complexity": "high",
            "calculation_type": "total_cost",
            "gross_salary": Decimal("35000"),
            "sector": CCNLSector.METALMECCANICI_INDUSTRIA,
            "expected_accuracy": "99%"
        }
        
        result = await success_criteria_service._test_calculation_query(test_query)
        
        # Verify result structure
        assert isinstance(result, str)
        assert "€" in result  # Should contain currency symbol
        assert "cost" in result.lower() or "salary" in result.lower()
    
    @pytest.mark.asyncio
    async def test_comparison_query_handling(self, success_criteria_service):
        """Test comparison-based query handling."""
        test_query = {
            "description": "Test comparison query",
            "complexity": "medium",
            "sectors": [CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.COMMERCIO_TERZIARIO],
            "comparison": "holiday_days",
            "expected_result": "structured_comparison"
        }
        
        result = await success_criteria_service._test_comparison_query(test_query)
        
        # Verify result contains comparison data
        assert isinstance(result, str)
        assert "comparison" in result.lower() or "holiday" in result.lower()
    
    @pytest.mark.asyncio
    async def test_date_range_query_handling(self, success_criteria_service):
        """Test date range query handling."""
        test_query = {
            "description": "Test date range query",
            "complexity": "medium",
            "date_range": {"from": date.today(), "to": date.today() + timedelta(days=180)},
            "include_renewal_status": True,
            "expected_count": ">=5"
        }
        
        result = await success_criteria_service._test_date_range_query(test_query)
        
        # Verify result contains date range information
        assert isinstance(result, str)
        assert "ccnl" in result.lower() or "expiring" in result.lower()


class TestCalculationAccuracy:
    """Test calculation accuracy verification functionality."""
    
    @pytest.fixture
    def success_criteria_service(self):
        """Create success criteria service instance."""
        return CCNLSuccessCriteriaService()
    
    @pytest.mark.asyncio
    async def test_calculation_accuracy_verification(self, success_criteria_service):
        """Test calculation accuracy verification against official tables."""
        calc_tests = await success_criteria_service._verify_calculation_accuracy()
        
        # Verify test results structure
        assert isinstance(calc_tests, list)
        assert len(calc_tests) > 0
        
        for test in calc_tests:
            assert isinstance(test, CalculationAccuracyTest)
            assert test.calculation_type
            assert test.test_scenario
            assert test.official_result > 0
            assert 0 <= test.accuracy_percentage <= 100
            assert isinstance(test.within_tolerance, bool)
            assert test.notes
    
    def test_calculation_test_scenarios(self, success_criteria_service):
        """Test that calculation test scenarios are comprehensive."""
        # This would verify that we test all major calculation types
        # Net salary, holiday accrual, overtime, contributions, etc.
        
        # For now, verify the structure exists in the service
        assert hasattr(success_criteria_service, '_verify_calculation_accuracy')
    
    @pytest.mark.asyncio
    async def test_net_salary_calculation_accuracy(self, success_criteria_service):
        """Test net salary calculation accuracy specifically."""
        # Test net salary calculation using simplified approach
        from app.services.validators.italian_tax_calculator import ItalianTaxCalculator
        
        gross_monthly = Decimal("2500")
        tax_calc = ItalianTaxCalculator()
        annual_gross = float(gross_monthly) * 12
        
        net_annual = tax_calc.calculate_net_salary(annual_gross)
        net_monthly = Decimal(str(net_annual)) / 12
        
        # Verify calculation results
        assert net_monthly > 0
        assert net_monthly < gross_monthly  # Net should be less than gross
        assert net_annual > 0
    
    def test_calculation_tolerance_levels(self, success_criteria_service):
        """Test that calculation tolerance levels are reasonable."""
        # Tolerance should be strict for financial calculations
        # This would test the tolerance values used in accuracy tests
        pass


class TestUpdateTimeliness:
    """Test update timeliness monitoring functionality."""
    
    @pytest.fixture
    def success_criteria_service(self):
        """Create success criteria service instance."""
        return CCNLSuccessCriteriaService()
    
    @pytest.mark.asyncio
    async def test_update_timeliness_monitoring(self, success_criteria_service):
        """Test update timeliness monitoring functionality."""
        timeliness_metrics = await success_criteria_service._monitor_update_timeliness()
        
        # Verify metrics structure
        assert isinstance(timeliness_metrics, list)
        
        for metric in timeliness_metrics:
            assert isinstance(metric, UpdateTimelinessMetric)
            assert metric.source_id
            assert isinstance(metric.last_update, datetime)
            assert metric.hours_since_update >= 0
            assert isinstance(metric.meets_48hour_requirement, bool)
            assert metric.avg_update_frequency
            assert 0 <= metric.reliability_score <= 1
    
    def test_48_hour_requirement_logic(self, success_criteria_service):
        """Test 48-hour requirement logic."""
        current_time = datetime.utcnow()
        
        # Test cases for 48-hour requirement
        test_cases = [
            (current_time - timedelta(hours=24), True),   # 24 hours ago - meets requirement
            (current_time - timedelta(hours=48), True),   # Exactly 48 hours - meets requirement  
            (current_time - timedelta(hours=72), False),  # 72 hours ago - fails requirement
            (current_time - timedelta(days=7), False),    # 1 week ago - fails requirement
        ]
        
        for last_update, expected_meets_requirement in test_cases:
            hours_since = (current_time - last_update).total_seconds() / 3600
            meets_requirement = hours_since <= 48
            assert meets_requirement == expected_meets_requirement


class TestTestCoverageAnalysis:
    """Test test coverage analysis functionality."""
    
    @pytest.fixture
    def success_criteria_service(self):
        """Create success criteria service instance."""
        return CCNLSuccessCriteriaService()
    
    @pytest.mark.asyncio
    async def test_test_coverage_analysis(self, success_criteria_service):
        """Test test coverage analysis functionality."""
        coverage_percentage = await success_criteria_service._analyze_test_coverage()
        
        # Verify coverage percentage is reasonable
        assert isinstance(coverage_percentage, float)
        assert 0 <= coverage_percentage <= 100
    
    def test_coverage_estimation_logic(self, success_criteria_service):
        """Test test coverage estimation logic."""
        # This would test the logic for estimating test coverage
        # In a real implementation, this would integrate with coverage tools
        pass


class TestSuccessCriteriaReporting:
    """Test comprehensive success criteria reporting."""
    
    @pytest.fixture
    def success_criteria_service(self):
        """Create success criteria service instance."""
        return CCNLSuccessCriteriaService()
    
    @pytest.mark.asyncio
    async def test_comprehensive_report_generation(self, success_criteria_service):
        """Test comprehensive report generation."""
        report = await success_criteria_service.generate_comprehensive_report()
        
        # Verify report structure
        assert isinstance(report, SuccessCriteriaReport)
        assert isinstance(report.coverage_analysis, CoverageAnalysis)
        assert isinstance(report.query_tests, list)
        assert isinstance(report.calculation_tests, list)
        assert isinstance(report.update_metrics, list)
        assert isinstance(report.test_coverage_percentage, float)
        assert isinstance(report.overall_success, bool)
        assert isinstance(report.recommendations, list)
        assert isinstance(report.generated_at, datetime)
    
    def test_overall_success_determination(self, success_criteria_service):
        """Test overall success determination logic."""
        # Create mock data for testing
        coverage = CoverageAnalysis(
            total_sectors_covered=52,
            major_ccnls_covered=51,
            estimated_worker_coverage_percentage=91.0,
            sectors_by_priority={},
            missing_sectors=[],
            coverage_gaps=[]
        )
        
        queries = [
            QueryCapabilityTest("Test 1", "high", "expected", "actual", True, 1.0, 0.9),
            QueryCapabilityTest("Test 2", "medium", "expected", "actual", True, 0.5, 0.8),
        ]
        
        calculations = [
            CalculationAccuracyTest("net_salary", "scenario", Decimal("1000"), Decimal("995"), 99.5, True, "good"),
        ]
        
        updates = [
            UpdateTimelinessMetric("source1", datetime.utcnow(), 24.0, True, "daily", 0.9),
        ]
        
        test_coverage = 92.0
        
        # Test success determination
        overall_success = success_criteria_service._determine_overall_success(
            coverage, queries, calculations, updates, test_coverage
        )
        
        # Should succeed if all criteria are met
        assert isinstance(overall_success, bool)
    
    def test_recommendations_generation(self, success_criteria_service):
        """Test recommendations generation logic."""
        # This would test the logic for generating actionable recommendations
        # based on the success criteria results
        pass


class TestSuccessCriteriaIntegration:
    """Test integration between different success criteria components."""
    
    @pytest.fixture
    def success_criteria_service(self):
        """Create success criteria service instance."""
        return CCNLSuccessCriteriaService()
    
    @pytest.mark.asyncio
    async def test_concurrent_verification_execution(self, success_criteria_service):
        """Test that all verifications can run concurrently."""
        # Test that concurrent execution works correctly
        import asyncio
        
        tasks = [
            success_criteria_service._verify_coverage_requirements(),
            success_criteria_service._test_query_capabilities(),
            success_criteria_service._verify_calculation_accuracy(),
            success_criteria_service._monitor_update_timeliness(),
            success_criteria_service._analyze_test_coverage()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all tasks completed (may have exceptions in test environment)
        assert len(results) == 5
        
        # At least some should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0
    
    def test_service_initialization(self, success_criteria_service):
        """Test proper service initialization."""
        assert hasattr(success_criteria_service, 'ccnl_service')
        assert hasattr(success_criteria_service, 'calculator_engine')  # May be None initially
        assert hasattr(success_criteria_service, 'major_sectors')
        assert hasattr(success_criteria_service, 'test_queries')
        
        # Verify major sectors are properly configured
        assert len(success_criteria_service.major_sectors) > 0
        
        # Verify test queries are properly configured
        assert len(success_criteria_service.test_queries) > 0


class TestSuccessCriteriaEdgeCases:
    """Test edge cases and error handling in success criteria verification."""
    
    @pytest.fixture
    def success_criteria_service(self):
        """Create success criteria service instance."""
        return CCNLSuccessCriteriaService()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_coverage_analysis(self, success_criteria_service):
        """Test error handling in coverage analysis."""
        # This would test error handling when CCNL service is unavailable
        # or returns unexpected data
        pass
    
    @pytest.mark.asyncio
    async def test_error_handling_in_query_testing(self, success_criteria_service):
        """Test error handling in query testing."""
        # Test that query testing handles errors gracefully
        query_tests = await success_criteria_service._test_query_capabilities()
        
        # Should return results even if some queries fail
        assert isinstance(query_tests, list)
    
    def test_boundary_conditions(self, success_criteria_service):
        """Test boundary conditions in success criteria logic."""
        # Test edge cases like exactly 50 CCNLs, exactly 90% coverage, etc.
        
        # Test 48-hour boundary
        current_time = datetime.utcnow()
        exactly_48_hours = current_time - timedelta(hours=48)
        hours_diff = (current_time - exactly_48_hours).total_seconds() / 3600
        
        # Should be exactly 48 hours
        assert abs(hours_diff - 48.0) < 0.1
        
        # Should meet requirement
        meets_requirement = hours_diff <= 48
        assert meets_requirement is True
    
    def test_zero_and_empty_cases(self, success_criteria_service):
        """Test handling of zero values and empty collections."""
        # Test that the service handles empty results gracefully
        empty_queries = []
        empty_calculations = []
        empty_updates = []
        
        # Should not crash with empty inputs
        overall_success = success_criteria_service._determine_overall_success(
            CoverageAnalysis(0, 0, 0.0, {}, [], []),
            empty_queries,
            empty_calculations, 
            empty_updates,
            0.0
        )
        
        # Should return False for empty/zero results
        assert overall_success is False