"""
TDD Tests for Main Financial Validation Engine.

This module tests the central orchestration engine that coordinates all financial
validation components: tax calculations, business valuations, financial analysis,
labor calculations, and document processing.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch

# These imports will fail initially - that's the TDD approach
from app.services.validators.financial_validation_engine import (
    FinancialValidationEngine,
    ValidationRequest,
    ValidationResult,
    ValidationTask,
    TaskType,
    EngineConfiguration,
    ValidationContext,
    ValidationError,
    ValidationWarning,
    TaskResult,
    QualityAssurance,
    ResultAggregation,
    PerformanceMetrics
)


class TestFinancialValidationEngine:
    """Test suite for Financial Validation Engine using TDD methodology."""
    
    @pytest.fixture
    def engine(self):
        """Create financial validation engine instance for tests."""
        config = EngineConfiguration(
            enable_tax_calculations=True,
            enable_business_valuations=True,
            enable_financial_ratios=True,
            enable_labor_calculations=True,
            enable_document_parsing=True,
            precision_decimal_places=2,
            performance_timeout_seconds=30,
            quality_threshold=Decimal('0.95')
        )
        return FinancialValidationEngine(config)
    
    @pytest.fixture
    def comprehensive_validation_request(self):
        """Comprehensive validation request covering all modules."""
        return ValidationRequest(
            request_id="test_req_001",
            user_id="user_123",
            session_id="session_456",
            timestamp=datetime.now(),
            tasks=[
                ValidationTask(
                    task_id="tax_calc_001",
                    task_type=TaskType.TAX_CALCULATION,
                    input_data={
                        'gross_income': Decimal('50000'),
                        'deductions': [{'type': 'employee', 'amount': Decimal('1000')}],
                        'tax_year': 2024
                    },
                    priority="high"
                ),
                ValidationTask(
                    task_id="business_val_001",
                    task_type=TaskType.BUSINESS_VALUATION,
                    input_data={
                        'cash_flows': [Decimal('100000')] * 5,
                        'discount_rate': Decimal('0.10'),
                        'terminal_growth_rate': Decimal('0.03')
                    },
                    priority="medium"
                ),
                ValidationTask(
                    task_id="financial_ratios_001",
                    task_type=TaskType.FINANCIAL_ANALYSIS,
                    input_data={
                        'balance_sheet': {
                            'current_assets': Decimal('500000'),
                            'current_liabilities': Decimal('300000'),
                            'total_assets': Decimal('2000000')
                        },
                        'income_statement': {
                            'revenue': Decimal('3000000'),
                            'net_income': Decimal('300000')
                        }
                    },
                    priority="medium"
                ),
                ValidationTask(
                    task_id="labor_calc_001",
                    task_type=TaskType.LABOR_CALCULATION,
                    input_data={
                        'gross_salary': Decimal('35000'),
                        'contract_type': 'permanent',
                        'hire_date': date(2020, 1, 15)
                    },
                    priority="low"
                )
            ],
            context=ValidationContext(
                language="it",
                region="italy",
                currency="EUR",
                regulation_year=2024
            )
        )
    
    # =========================================================================
    # Engine Initialization and Configuration Tests
    # =========================================================================
    
    def test_engine_initialization_with_all_modules(self, engine):
        """Test engine initialization with all validation modules enabled."""
        # Assert
        assert engine.config.enable_tax_calculations is True
        assert engine.config.enable_business_valuations is True
        assert engine.config.enable_financial_ratios is True
        assert engine.config.enable_labor_calculations is True
        assert engine.config.enable_document_parsing is True
        
        # Check that all calculators are initialized
        assert engine.tax_calculator is not None
        assert engine.business_valuation_engine is not None
        assert engine.financial_ratios_calculator is not None
        assert engine.labor_calculator is not None
        assert engine.document_parser is not None
        
        # Check engine state
        assert engine.is_ready is True
        assert engine.supported_task_types == [
            TaskType.TAX_CALCULATION,
            TaskType.BUSINESS_VALUATION,
            TaskType.FINANCIAL_ANALYSIS,
            TaskType.LABOR_CALCULATION,
            TaskType.DOCUMENT_PARSING,
            TaskType.BUSINESS_PLAN_GENERATION
        ]
    
    def test_engine_initialization_selective_modules(self):
        """Test engine initialization with only selected modules enabled."""
        # Arrange
        selective_config = EngineConfiguration(
            enable_tax_calculations=True,
            enable_business_valuations=False,  # Disabled
            enable_financial_ratios=True,
            enable_labor_calculations=False,   # Disabled
            enable_document_parsing=True
        )
        
        # Act
        selective_engine = FinancialValidationEngine(selective_config)
        
        # Assert
        assert selective_engine.tax_calculator is not None
        assert selective_engine.business_valuation_engine is None
        assert selective_engine.financial_ratios_calculator is not None
        assert selective_engine.labor_calculator is None
        assert selective_engine.document_parser is not None
        
        # Should only support enabled task types
        supported_types = selective_engine.supported_task_types
        assert TaskType.TAX_CALCULATION in supported_types
        assert TaskType.BUSINESS_VALUATION not in supported_types
        assert TaskType.FINANCIAL_ANALYSIS in supported_types
        assert TaskType.LABOR_CALCULATION not in supported_types
    
    # =========================================================================
    # Single Task Validation Tests
    # =========================================================================
    
    def test_single_tax_calculation_task(self, engine):
        """Test execution of single tax calculation task."""
        # Arrange
        tax_task = ValidationTask(
            task_id="tax_001",
            task_type=TaskType.TAX_CALCULATION,
            input_data={
                'calculation_type': 'irpef',
                'gross_income': Decimal('30000'),
                'deductions': [],
                'tax_credits': []
            }
        )
        
        # Act
        result = engine.execute_single_task(tax_task)
        
        # Assert
        assert isinstance(result, TaskResult)
        assert result.task_id == "tax_001"
        assert result.success is True
        assert result.execution_time_ms > 0
        assert result.execution_time_ms < 5000  # Should be fast
        
        # Check tax calculation result
        assert result.output_data['tax_amount'] > Decimal('0')
        assert result.output_data['effective_rate'] > Decimal('0')
        assert result.quality_score >= Decimal('0.95')  # High quality expected
        
        # Should include calculation metadata
        assert 'formula' in result.output_data
        assert 'calculation_steps' in result.output_data
        assert result.validation_warnings == []  # No warnings expected
    
    def test_single_business_valuation_task(self, engine):
        """Test execution of single business valuation task."""
        # Arrange
        valuation_task = ValidationTask(
            task_id="val_001",
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                'valuation_method': 'dcf',
                'cash_flows': [Decimal('50000')] * 5,
                'discount_rate': Decimal('0.12'),
                'terminal_growth_rate': Decimal('0.02')
            }
        )
        
        # Act
        result = engine.execute_single_task(valuation_task)
        
        # Assert
        assert result.success is True
        assert result.output_data['enterprise_value'] > Decimal('0')
        assert result.output_data['terminal_value'] > Decimal('0')
        assert len(result.output_data['pv_cash_flows']) == 5
        
        # Should include confidence metrics
        assert result.output_data['confidence_score'] >= Decimal('0.8')
        assert result.quality_score >= Decimal('0.90')
    
    def test_single_document_parsing_task(self, engine):
        """Test execution of single document parsing task."""
        # Arrange
        parsing_task = ValidationTask(
            task_id="doc_001",
            task_type=TaskType.DOCUMENT_PARSING,
            input_data={
                'document_path': '/path/to/financial_statement.xlsx',
                'document_type': 'balance_sheet',
                'expected_format': 'excel'
            }
        )
        
        # Mock the document parser to avoid file system dependencies
        with patch.object(engine.document_parser, 'parse_document') as mock_parse:
            mock_parse.return_value = {
                'current_assets': Decimal('500000'),
                'total_assets': Decimal('2000000'),
                'extraction_confidence': Decimal('0.92'),
                'validation_errors': []
            }
            
            # Act
            result = engine.execute_single_task(parsing_task)
            
            # Assert
            assert result.success is True
            assert result.output_data['current_assets'] == Decimal('500000')
            assert result.output_data['extraction_confidence'] >= Decimal('0.90')
    
    # =========================================================================
    # Multi-Task Pipeline Execution Tests
    # =========================================================================
    
    def test_sequential_pipeline_execution(self, engine, comprehensive_validation_request):
        """Test sequential execution of multiple validation tasks."""
        # Act
        pipeline_result = engine.execute_pipeline(
            comprehensive_validation_request,
            execution_mode='sequential'
        )
        
        # Assert
        assert isinstance(pipeline_result, ValidationResult)
        assert pipeline_result.request_id == "test_req_001"
        assert pipeline_result.total_tasks == 4
        assert pipeline_result.successful_tasks >= 3  # Most should succeed
        assert pipeline_result.failed_tasks <= 1      # At most one failure acceptable
        
        # Check individual task results
        task_results = pipeline_result.task_results
        assert len(task_results) == 4
        
        # Tax calculation task should succeed
        tax_result = next(r for r in task_results if r.task_id == "tax_calc_001")
        assert tax_result.success is True
        assert tax_result.output_data['tax_amount'] > Decimal('0')
        
        # Business valuation task should succeed
        val_result = next(r for r in task_results if r.task_id == "business_val_001")
        assert val_result.success is True
        assert val_result.output_data['enterprise_value'] > Decimal('0')
        
        # Check overall execution metrics
        assert pipeline_result.total_execution_time_ms > 0
        assert pipeline_result.average_task_time_ms > 0
        assert pipeline_result.overall_quality_score >= Decimal('0.85')
    
    def test_parallel_pipeline_execution(self, engine, comprehensive_validation_request):
        """Test parallel execution of multiple validation tasks."""
        # Act
        pipeline_result = engine.execute_pipeline(
            comprehensive_validation_request,
            execution_mode='parallel'
        )
        
        # Assert
        assert pipeline_result.success_rate >= Decimal('0.75')  # 75% success rate minimum
        assert pipeline_result.execution_mode == 'parallel'
        
        # Parallel execution should be faster than sequential for multiple tasks
        # (This would be verified in integration tests with actual timing)
        assert pipeline_result.parallelization_efficiency >= Decimal('1.2')  # At least 20% improvement
        
        # All high-priority tasks should complete successfully
        high_priority_results = [r for r in pipeline_result.task_results if r.priority == "high"]
        assert all(r.success for r in high_priority_results)
    
    def test_pipeline_with_task_dependencies(self, engine):
        """Test pipeline execution with task dependencies."""
        # Arrange - Create tasks with dependencies
        dependent_request = ValidationRequest(
            request_id="dep_req_001",
            tasks=[
                ValidationTask(
                    task_id="parse_doc",
                    task_type=TaskType.DOCUMENT_PARSING,
                    input_data={'document_path': '/path/to/financial_data.xlsx'},
                    dependencies=[]
                ),
                ValidationTask(
                    task_id="calc_ratios",
                    task_type=TaskType.FINANCIAL_ANALYSIS,
                    input_data={'use_parsed_data': True},
                    dependencies=["parse_doc"]  # Depends on document parsing
                ),
                ValidationTask(
                    task_id="business_val",
                    task_type=TaskType.BUSINESS_VALUATION,
                    input_data={'use_financial_ratios': True},
                    dependencies=["calc_ratios"]  # Depends on ratio calculation
                )
            ]
        )
        
        # Mock successful document parsing
        with patch.object(engine.document_parser, 'parse_document') as mock_parse:
            mock_parse.return_value = {
                'revenue': Decimal('1000000'),
                'net_income': Decimal('100000'),
                'total_assets': Decimal('800000')
            }
            
            # Act
            result = engine.execute_pipeline_with_dependencies(dependent_request)
            
            # Assert
            assert result.dependency_resolution_successful is True
            assert len(result.execution_order) == 3
            assert result.execution_order[0] == "parse_doc"     # First
            assert result.execution_order[1] == "calc_ratios"  # Second
            assert result.execution_order[2] == "business_val" # Last
            
            # Each task should have access to previous task outputs
            ratio_task_result = next(r for r in result.task_results if r.task_id == "calc_ratios")
            assert ratio_task_result.input_data['revenue'] == Decimal('1000000')
    
    # =========================================================================
    # Error Handling and Recovery Tests
    # =========================================================================
    
    def test_pipeline_error_handling_continue_on_failure(self, engine):
        """Test pipeline continues execution when individual tasks fail."""
        # Arrange - Create request with one task that will fail
        mixed_request = ValidationRequest(
            request_id="mixed_req_001",
            tasks=[
                ValidationTask(
                    task_id="good_task",
                    task_type=TaskType.TAX_CALCULATION,
                    input_data={'gross_income': Decimal('30000')}
                ),
                ValidationTask(
                    task_id="bad_task",
                    task_type=TaskType.TAX_CALCULATION,
                    input_data={'gross_income': Decimal('-1000')}  # Invalid negative income
                ),
                ValidationTask(
                    task_id="another_good_task",
                    task_type=TaskType.FINANCIAL_ANALYSIS,
                    input_data={
                        'balance_sheet': {'current_assets': Decimal('100000')},
                        'income_statement': {'revenue': Decimal('500000')}
                    }
                )
            ],
            error_handling_strategy='continue_on_failure'
        )
        
        # Act
        result = engine.execute_pipeline(mixed_request)
        
        # Assert
        assert result.successful_tasks == 2  # Two good tasks
        assert result.failed_tasks == 1     # One bad task
        assert result.overall_success is True  # Continue on failure = overall success
        
        # Check specific results
        good_result = next(r for r in result.task_results if r.task_id == "good_task")
        assert good_result.success is True
        
        bad_result = next(r for r in result.task_results if r.task_id == "bad_task")
        assert bad_result.success is False
        assert len(bad_result.error_messages) >= 1
        assert 'negative' in bad_result.error_messages[0].lower()
        
        another_good_result = next(r for r in result.task_results if r.task_id == "another_good_task")
        assert another_good_result.success is True
    
    def test_pipeline_error_handling_fail_fast(self, engine):
        """Test pipeline stops execution on first failure when configured to fail fast."""
        # Arrange
        fail_fast_request = ValidationRequest(
            request_id="fail_fast_001",
            tasks=[
                ValidationTask(
                    task_id="first_task",
                    task_type=TaskType.TAX_CALCULATION,
                    input_data={'gross_income': Decimal('-5000')}  # Will fail
                ),
                ValidationTask(
                    task_id="second_task",
                    task_type=TaskType.FINANCIAL_ANALYSIS,
                    input_data={'valid': 'data'}  # Would succeed but shouldn't execute
                )
            ],
            error_handling_strategy='fail_fast'
        )
        
        # Act
        result = engine.execute_pipeline(fail_fast_request)
        
        # Assert
        assert result.overall_success is False
        assert result.failed_tasks >= 1
        assert result.execution_stopped_early is True
        
        # Second task should not have executed
        second_task_result = next((r for r in result.task_results if r.task_id == "second_task"), None)
        assert second_task_result is None or second_task_result.status == "not_executed"
    
    def test_task_timeout_handling(self, engine):
        """Test handling of tasks that exceed timeout limits."""
        # Arrange
        timeout_task = ValidationTask(
            task_id="slow_task",
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                'cash_flows': [Decimal('100000')] * 20,  # Large calculation
                'simulation_runs': 10000  # Lots of Monte Carlo simulations
            },
            timeout_seconds=1  # Very short timeout
        )
        
        # Act
        result = engine.execute_single_task(timeout_task)
        
        # Assert
        assert result.success is False
        assert result.timeout_occurred is True
        assert result.execution_time_ms >= 1000  # At least 1 second (timeout)
        assert 'timeout' in result.error_messages[0].lower()
        
        # Engine should remain stable after timeout
        assert engine.is_ready is True
    
    # =========================================================================
    # Quality Assurance and Validation Tests
    # =========================================================================
    
    def test_quality_assurance_cross_validation(self, engine):
        """Test quality assurance with cross-validation between modules."""
        # Arrange - Request that can be validated multiple ways
        cross_val_request = ValidationRequest(
            request_id="cross_val_001",
            tasks=[
                ValidationTask(
                    task_id="tax_calc_primary",
                    task_type=TaskType.TAX_CALCULATION,
                    input_data={
                        'gross_income': Decimal('40000'),
                        'calculation_method': 'standard'
                    }
                ),
                ValidationTask(
                    task_id="tax_calc_alternative",
                    task_type=TaskType.TAX_CALCULATION,
                    input_data={
                        'gross_income': Decimal('40000'),
                        'calculation_method': 'detailed'
                    }
                )
            ],
            quality_assurance=QualityAssurance(
                enable_cross_validation=True,
                variance_threshold=Decimal('0.05'),  # 5% maximum variance
                confidence_threshold=Decimal('0.90')
            )
        )
        
        # Act
        result = engine.execute_pipeline_with_qa(cross_val_request)
        
        # Assert
        assert result.cross_validation_performed is True
        assert len(result.cross_validation_results) >= 1
        
        # Check variance between calculation methods
        cross_val_result = result.cross_validation_results[0]
        assert cross_val_result.variance_percentage <= Decimal('5.0')  # Within 5%
        assert cross_val_result.confidence_level >= Decimal('0.90')
        
        # Should provide consolidated result with higher confidence
        assert result.consolidated_result is not None
        assert result.consolidated_result.confidence_score > Decimal('0.90')
    
    def test_result_aggregation_and_summary(self, engine, comprehensive_validation_request):
        """Test result aggregation and summary generation."""
        # Act
        result = engine.execute_pipeline(comprehensive_validation_request)
        aggregated = engine.aggregate_results(result)
        
        # Assert
        assert isinstance(aggregated, ResultAggregation)
        assert aggregated.total_calculations_performed >= 4
        assert aggregated.overall_confidence >= Decimal('0.80')
        
        # Should provide summary by category
        assert 'tax_calculations' in aggregated.results_by_category
        assert 'business_valuations' in aggregated.results_by_category
        assert 'financial_analysis' in aggregated.results_by_category
        
        # Should identify key insights
        assert len(aggregated.key_insights) >= 3
        assert len(aggregated.recommendations) >= 2
        
        # Should provide executive summary
        assert aggregated.executive_summary is not None
        assert len(aggregated.executive_summary) > 100  # Substantial summary
        assert 'tax' in aggregated.executive_summary.lower()
        assert 'valuation' in aggregated.executive_summary.lower()
    
    def test_performance_metrics_tracking(self, engine, comprehensive_validation_request):
        """Test performance metrics tracking and reporting."""
        # Act
        result = engine.execute_pipeline(comprehensive_validation_request)
        
        # Assert
        assert isinstance(result.performance_metrics, PerformanceMetrics)
        
        # Should track timing metrics
        assert result.performance_metrics.total_execution_time_ms > 0
        assert result.performance_metrics.average_task_time_ms > 0
        assert result.performance_metrics.slowest_task_time_ms >= result.performance_metrics.average_task_time_ms
        
        # Should track resource usage
        assert result.performance_metrics.peak_memory_usage_mb > 0
        assert result.performance_metrics.cpu_utilization_percentage >= 0
        
        # Should track quality metrics
        assert result.performance_metrics.average_quality_score >= Decimal('0.80')
        assert result.performance_metrics.quality_variance <= Decimal('0.20')
        
        # Should identify performance bottlenecks
        if result.performance_metrics.total_execution_time_ms > 5000:  # If slow
            assert len(result.performance_metrics.bottleneck_analysis) >= 1
    
    # =========================================================================
    # Integration and End-to-End Tests
    # =========================================================================
    
    def test_end_to_end_financial_analysis_workflow(self, engine):
        """Test complete end-to-end financial analysis workflow."""
        # Arrange - Complete financial analysis scenario
        e2e_request = ValidationRequest(
            request_id="e2e_001",
            tasks=[
                # 1. Parse financial documents
                ValidationTask(
                    task_id="parse_statements",
                    task_type=TaskType.DOCUMENT_PARSING,
                    input_data={
                        'balance_sheet_path': '/path/to/balance_sheet.xlsx',
                        'income_statement_path': '/path/to/income_statement.xlsx'
                    }
                ),
                # 2. Calculate financial ratios
                ValidationTask(
                    task_id="financial_ratios",
                    task_type=TaskType.FINANCIAL_ANALYSIS,
                    input_data={'use_parsed_statements': True},
                    dependencies=["parse_statements"]
                ),
                # 3. Perform business valuation
                ValidationTask(
                    task_id="business_valuation",
                    task_type=TaskType.BUSINESS_VALUATION,
                    input_data={'use_financial_data': True},
                    dependencies=["financial_ratios"]
                ),
                # 4. Calculate tax implications
                ValidationTask(
                    task_id="tax_analysis",
                    task_type=TaskType.TAX_CALCULATION,
                    input_data={'income_from_valuation': True},
                    dependencies=["business_valuation"]
                ),
                # 5. Generate business plan
                ValidationTask(
                    task_id="business_plan",
                    task_type=TaskType.BUSINESS_PLAN_GENERATION,
                    input_data={'use_all_analyses': True},
                    dependencies=["financial_ratios", "business_valuation", "tax_analysis"]
                )
            ]
        )
        
        # Mock document parsing to provide realistic data
        with patch.object(engine.document_parser, 'parse_document') as mock_parse:
            mock_parse.return_value = {
                'balance_sheet': {
                    'current_assets': Decimal('800000'),
                    'total_assets': Decimal('3000000'),
                    'current_liabilities': Decimal('400000'),
                    'shareholders_equity': Decimal('2000000')
                },
                'income_statement': {
                    'revenue': Decimal('5000000'),
                    'net_income': Decimal('500000'),
                    'ebitda': Decimal('750000')
                }
            }
            
            # Act
            result = engine.execute_comprehensive_workflow(e2e_request)
            
            # Assert
            assert result.workflow_completed is True
            assert result.successful_tasks >= 4  # Most tasks should succeed
            assert result.data_flow_integrity is True  # Data should flow correctly between tasks
            
            # Check that each step used data from previous steps
            ratio_result = next(r for r in result.task_results if r.task_id == "financial_ratios")
            assert ratio_result.success is True
            assert 'current_ratio' in ratio_result.output_data
            
            valuation_result = next(r for r in result.task_results if r.task_id == "business_valuation")
            assert valuation_result.success is True
            assert valuation_result.output_data['enterprise_value'] > Decimal('0')
            
            # Final business plan should incorporate all analyses
            plan_result = next(r for r in result.task_results if r.task_id == "business_plan")
            assert plan_result.success is True
            assert len(plan_result.output_data['sections']) >= 5
    
    # =========================================================================
    # Configuration and Customization Tests
    # =========================================================================
    
    def test_engine_reconfiguration_runtime(self, engine):
        """Test runtime reconfiguration of engine settings."""
        # Arrange - New configuration
        new_config = EngineConfiguration(
            enable_tax_calculations=True,
            enable_business_valuations=True,
            enable_financial_ratios=False,  # Disable this module
            precision_decimal_places=4,     # Higher precision
            performance_timeout_seconds=60  # Longer timeout
        )
        
        # Act
        reconfiguration_success = engine.reconfigure(new_config)
        
        # Assert
        assert reconfiguration_success is True
        assert engine.config.precision_decimal_places == 4
        assert engine.config.performance_timeout_seconds == 60
        assert engine.financial_ratios_calculator is None  # Should be disabled
        
        # Should still be ready with remaining modules
        assert engine.is_ready is True
        assert TaskType.FINANCIAL_ANALYSIS not in engine.supported_task_types
    
    def test_custom_validation_rules(self, engine):
        """Test addition of custom validation rules."""
        # Arrange - Custom validation rule
        def custom_italian_tax_rule(tax_data):
            """Custom rule: Tax rate should not exceed 50% for any bracket."""
            if tax_data.get('effective_rate', 0) > Decimal('0.50'):
                return ValidationWarning(
                    code="HIGH_TAX_RATE",
                    message="Effective tax rate exceeds 50%",
                    severity="medium"
                )
            return None
        
        # Act
        engine.add_custom_validation_rule('italian_tax_limit', custom_italian_tax_rule)
        
        # Test with high income that would trigger rule
        high_income_task = ValidationTask(
            task_id="high_tax_test",
            task_type=TaskType.TAX_CALCULATION,
            input_data={'gross_income': Decimal('150000')}  # High income
        )
        
        result = engine.execute_single_task(high_income_task)
        
        # Assert
        assert 'italian_tax_limit' in engine.custom_validation_rules
        # If effective rate is high, should have warning
        if result.output_data.get('effective_rate', Decimal('0')) > Decimal('0.50'):
            assert len(result.validation_warnings) >= 1
            assert any('HIGH_TAX_RATE' in w.code for w in result.validation_warnings)
    
    # =========================================================================
    # Performance and Scalability Tests
    # =========================================================================
    
    def test_engine_performance_high_volume(self, engine):
        """Test engine performance with high volume of tasks."""
        import time
        
        # Arrange - Large number of tasks
        high_volume_tasks = []
        for i in range(50):  # 50 tasks
            high_volume_tasks.append(
                ValidationTask(
                    task_id=f"task_{i:03d}",
                    task_type=TaskType.TAX_CALCULATION,
                    input_data={'gross_income': Decimal(str(20000 + i * 1000))}
                )
            )
        
        high_volume_request = ValidationRequest(
            request_id="high_vol_001",
            tasks=high_volume_tasks
        )
        
        # Act
        start_time = time.time()
        result = engine.execute_pipeline(high_volume_request, execution_mode='parallel')
        end_time = time.time()
        
        # Assert
        total_time = end_time - start_time
        assert total_time < 30.0  # Should complete within 30 seconds
        assert result.successful_tasks >= 45  # At least 90% success rate
        
        # Average task time should be reasonable
        avg_task_time = result.average_task_time_ms
        assert avg_task_time < 500  # Less than 500ms per task on average
        
        # Parallel efficiency should be good
        assert result.parallelization_efficiency >= Decimal('2.0')  # At least 2x speedup
    
    def test_engine_memory_management(self, engine):
        """Test engine memory management with large datasets."""
        # Arrange - Task with large dataset
        large_data_task = ValidationTask(
            task_id="large_data",
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                'cash_flows': [Decimal(str(100000 + i)) for i in range(1000)],  # 1000 years
                'sensitivity_analysis': True,
                'monte_carlo_simulations': 10000
            }
        )
        
        # Act
        result = engine.execute_single_task(large_data_task)
        
        # Assert
        # Should handle large data without memory issues
        assert result.success is True or result.timeout_occurred is True
        
        # Memory usage should be tracked
        if hasattr(result, 'memory_usage_mb'):
            assert result.memory_usage_mb < 1000  # Less than 1GB
        
        # Engine should clean up after large operations
        post_execution_memory = engine.get_memory_usage_mb()
        assert post_execution_memory < 200  # Should return to reasonable baseline