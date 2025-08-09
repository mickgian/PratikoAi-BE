"""
Financial Validation API endpoints.

This module provides REST API endpoints for the Financial Validation Engine,
including tax calculations, business valuations, financial analysis, and document processing.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime, date
import uuid

from app.core.logging import logger
from app.services.validators.financial_validation_engine import (
    FinancialValidationEngine,
    ValidationRequest,
    ValidationTask,
    TaskType,
    EngineConfiguration,
    ValidationContext
)

router = APIRouter()

# Initialize the Financial Validation Engine
engine_config = EngineConfiguration(
    enable_tax_calculations=True,
    enable_business_valuations=True,
    enable_financial_ratios=True,
    enable_labor_calculations=True,
    enable_document_parsing=True,
    precision_decimal_places=2,
    performance_timeout_seconds=30,
    quality_threshold=Decimal('0.90')
)

validation_engine = FinancialValidationEngine(engine_config)


# Pydantic models for API requests/responses
class TaxCalculationRequest(BaseModel):
    """Request model for tax calculations."""
    gross_income: Decimal = Field(..., description="Gross annual income in EUR")
    deductions: List[Dict[str, Any]] = Field(default=[], description="List of tax deductions")
    tax_credits: List[Dict[str, Any]] = Field(default=[], description="List of tax credits")
    tax_year: int = Field(default=2024, description="Tax year for calculation")
    region: str = Field(default="italy", description="Tax region")

class BusinessValuationRequest(BaseModel):
    """Request model for business valuations."""
    cash_flows: List[Decimal] = Field(..., description="Projected cash flows")
    discount_rate: Decimal = Field(..., description="Discount rate (WACC)")
    terminal_growth_rate: Decimal = Field(default=Decimal('0.02'), description="Terminal growth rate")
    valuation_method: str = Field(default="dcf", description="Valuation method")

class FinancialAnalysisRequest(BaseModel):
    """Request model for financial analysis."""
    balance_sheet: Dict[str, Decimal] = Field(..., description="Balance sheet data")
    income_statement: Dict[str, Decimal] = Field(..., description="Income statement data")
    analysis_type: str = Field(default="comprehensive", description="Type of analysis")

class LaborCalculationRequest(BaseModel):
    """Request model for labor calculations."""
    gross_salary: Decimal = Field(..., description="Gross annual salary in EUR")
    contract_type: str = Field(default="permanent", description="Type of employment contract")
    hire_date: date = Field(..., description="Employee hire date")
    calculation_type: str = Field(default="comprehensive", description="Type of calculation")

class DocumentParsingRequest(BaseModel):
    """Request model for document parsing."""
    document_path: str = Field(..., description="Path to document file")
    document_type: str = Field(..., description="Type of document")
    expected_format: str = Field(..., description="Expected file format")

class ValidationTaskRequest(BaseModel):
    """Request model for creating validation tasks."""
    task_type: TaskType = Field(..., description="Type of validation task")
    input_data: Dict[str, Any] = Field(..., description="Input data for the task")
    priority: str = Field(default="medium", description="Task priority")

class MultiTaskValidationRequest(BaseModel):
    """Request model for multiple validation tasks."""
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    tasks: List[ValidationTaskRequest] = Field(..., description="List of validation tasks")
    execution_mode: str = Field(default="sequential", description="Execution mode")
    error_handling_strategy: str = Field(default="continue_on_failure", description="Error handling")

class ValidationResponse(BaseModel):
    """Response model for validation results."""
    success: bool = Field(..., description="Whether the validation succeeded")
    result_data: Dict[str, Any] = Field(..., description="Validation results")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    quality_score: Decimal = Field(..., description="Quality score (0-1)")
    confidence_score: Decimal = Field(..., description="Confidence score (0-1)")
    warnings: List[str] = Field(default=[], description="Validation warnings")
    errors: List[str] = Field(default=[], description="Validation errors")


@router.post("/tax/calculate", response_model=ValidationResponse, summary="Calculate Italian Taxes")
async def calculate_taxes(
    request: TaxCalculationRequest,
    background_tasks: BackgroundTasks
) -> ValidationResponse:
    """
    Calculate Italian taxes (IRPEF, IVA, IRES, IRAP) for individuals and companies.
    
    This endpoint provides comprehensive Italian tax calculations including:
    - IRPEF (Personal Income Tax) with progressive brackets
    - IVA (VAT) at standard rates (4%, 10%, 22%)
    - IRES (Corporate Tax) at 24%
    - IRAP (Regional Tax) at 3.9%
    
    **Example Request:**
    ```json
    {
        "gross_income": 50000,
        "deductions": [{"type": "employee", "amount": 1000}],
        "tax_credits": [{"type": "child", "amount": 800}],
        "tax_year": 2024
    }
    ```
    """
    try:
        task = ValidationTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.TAX_CALCULATION,
            input_data={
                "gross_income": request.gross_income,
                "deductions": request.deductions,
                "tax_credits": request.tax_credits,
                "tax_year": request.tax_year
            }
        )
        
        result = validation_engine.execute_single_task(task)
        
        logger.info(
            "tax_calculation_completed",
            gross_income=request.gross_income,
            success=result.success,
            execution_time_ms=result.execution_time_ms
        )
        
        return ValidationResponse(
            success=result.success,
            result_data=result.output_data,
            execution_time_ms=result.execution_time_ms,
            quality_score=result.quality_score,
            confidence_score=result.confidence_score,
            warnings=[w.message for w in result.validation_warnings],
            errors=result.error_messages
        )
        
    except Exception as e:
        logger.error("tax_calculation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Tax calculation failed: {str(e)}")


@router.post("/business/valuation", response_model=ValidationResponse, summary="Business Valuation")
async def business_valuation(
    request: BusinessValuationRequest
) -> ValidationResponse:
    """
    Perform business valuation using multiple methods (DCF, EBITDA multiples, asset-based).
    
    Supports various valuation approaches:
    - **DCF (Discounted Cash Flow)**: With terminal value calculations
    - **EBITDA Multiples**: Industry-specific multiple valuations
    - **Asset-Based**: Book value and liquidation value approaches
    
    **Example Request:**
    ```json
    {
        "cash_flows": [100000, 120000, 144000, 172800, 207360],
        "discount_rate": 0.10,
        "terminal_growth_rate": 0.03,
        "valuation_method": "dcf"
    }
    ```
    """
    try:
        task = ValidationTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                "cash_flows": request.cash_flows,
                "discount_rate": request.discount_rate,
                "terminal_growth_rate": request.terminal_growth_rate,
                "valuation_method": request.valuation_method
            }
        )
        
        result = validation_engine.execute_single_task(task)
        
        return ValidationResponse(
            success=result.success,
            result_data=result.output_data,
            execution_time_ms=result.execution_time_ms,
            quality_score=result.quality_score,
            confidence_score=result.confidence_score,
            warnings=[w.message for w in result.validation_warnings],
            errors=result.error_messages
        )
        
    except Exception as e:
        logger.error("business_valuation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Business valuation failed: {str(e)}")


@router.post("/financial/analysis", response_model=ValidationResponse, summary="Financial Ratio Analysis")
async def financial_analysis(
    request: FinancialAnalysisRequest
) -> ValidationResponse:
    """
    Perform comprehensive financial ratio analysis.
    
    Calculates key financial ratios including:
    - **Liquidity Ratios**: Current ratio, quick ratio, cash ratio
    - **Profitability Ratios**: ROA, ROE, profit margins
    - **Efficiency Ratios**: Asset turnover, inventory turnover
    - **Leverage Ratios**: Debt-to-equity, interest coverage
    
    **Example Request:**
    ```json
    {
        "balance_sheet": {
            "current_assets": 500000,
            "current_liabilities": 300000,
            "total_assets": 2000000,
            "shareholders_equity": 1200000
        },
        "income_statement": {
            "revenue": 3000000,
            "net_income": 300000
        }
    }
    ```
    """
    try:
        task = ValidationTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.FINANCIAL_ANALYSIS,
            input_data={
                "balance_sheet": request.balance_sheet,
                "income_statement": request.income_statement,
                "analysis_type": request.analysis_type
            }
        )
        
        result = validation_engine.execute_single_task(task)
        
        return ValidationResponse(
            success=result.success,
            result_data=result.output_data,
            execution_time_ms=result.execution_time_ms,
            quality_score=result.quality_score,
            confidence_score=result.confidence_score,
            warnings=[w.message for w in result.validation_warnings],
            errors=result.error_messages
        )
        
    except Exception as e:
        logger.error("financial_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Financial analysis failed: {str(e)}")


@router.post("/labor/calculate", response_model=ValidationResponse, summary="Labor Calculations")
async def labor_calculations(
    request: LaborCalculationRequest
) -> ValidationResponse:
    """
    Perform Italian labor calculations including TFR, contributions, and salary conversions.
    
    Calculations include:
    - **TFR (Trattamento di Fine Rapporto)**: End-of-service allowance
    - **INPS Contributions**: Employee and employer portions
    - **INAIL Insurance**: Workplace insurance calculations
    - **Salary Conversions**: Gross-to-net and net-to-gross
    
    **Example Request:**
    ```json
    {
        "gross_salary": 35000,
        "contract_type": "permanent",
        "hire_date": "2020-01-15",
        "calculation_type": "comprehensive"
    }
    ```
    """
    try:
        task = ValidationTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.LABOR_CALCULATION,
            input_data={
                "gross_salary": request.gross_salary,
                "contract_type": request.contract_type,
                "hire_date": request.hire_date,
                "calculation_type": request.calculation_type
            }
        )
        
        result = validation_engine.execute_single_task(task)
        
        return ValidationResponse(
            success=result.success,
            result_data=result.output_data,
            execution_time_ms=result.execution_time_ms,
            quality_score=result.quality_score,
            confidence_score=result.confidence_score,
            warnings=[w.message for w in result.validation_warnings],
            errors=result.error_messages
        )
        
    except Exception as e:
        logger.error("labor_calculation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Labor calculation failed: {str(e)}")


@router.post("/documents/parse", response_model=ValidationResponse, summary="Document Parsing")
async def parse_document(
    request: DocumentParsingRequest
) -> ValidationResponse:
    """
    Parse financial documents (Excel, PDF, CSV) and extract structured data.
    
    Supported document types:
    - **Excel**: Balance sheets, income statements, trial balances
    - **PDF**: Italian invoices with VAT calculations
    - **CSV**: Bank statements, transaction data
    
    **Example Request:**
    ```json
    {
        "document_path": "/path/to/financial_statement.xlsx",
        "document_type": "balance_sheet",
        "expected_format": "excel"
    }
    ```
    """
    try:
        task = ValidationTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.DOCUMENT_PARSING,
            input_data={
                "document_path": request.document_path,
                "document_type": request.document_type,
                "expected_format": request.expected_format
            }
        )
        
        result = validation_engine.execute_single_task(task)
        
        return ValidationResponse(
            success=result.success,
            result_data=result.output_data,
            execution_time_ms=result.execution_time_ms,
            quality_score=result.quality_score,
            confidence_score=result.confidence_score,
            warnings=[w.message for w in result.validation_warnings],
            errors=result.error_messages
        )
        
    except Exception as e:
        logger.error("document_parsing_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Document parsing failed: {str(e)}")


@router.post("/validate/pipeline", response_model=Dict[str, Any], summary="Multi-Task Validation Pipeline")
async def validation_pipeline(
    request: MultiTaskValidationRequest
) -> Dict[str, Any]:
    """
    Execute multiple validation tasks in a coordinated pipeline.
    
    Supports:
    - **Sequential Execution**: Tasks run one after another
    - **Parallel Execution**: Tasks run simultaneously 
    - **Dependency Management**: Tasks can depend on others
    - **Error Handling**: Continue-on-failure or fail-fast strategies
    
    **Example Request:**
    ```json
    {
        "tasks": [
            {
                "task_type": "tax_calculation",
                "input_data": {"gross_income": 50000},
                "priority": "high"
            },
            {
                "task_type": "business_valuation", 
                "input_data": {"cash_flows": [100000, 120000]},
                "priority": "medium"
            }
        ],
        "execution_mode": "sequential",
        "error_handling_strategy": "continue_on_failure"
    }
    ```
    """
    try:
        # Convert API request to engine format
        validation_tasks = []
        for task_req in request.tasks:
            task = ValidationTask(
                task_id=str(uuid.uuid4()),
                task_type=task_req.task_type,
                input_data=task_req.input_data,
                priority=task_req.priority
            )
            validation_tasks.append(task)
        
        validation_request = ValidationRequest(
            request_id=request.request_id or str(uuid.uuid4()),
            tasks=validation_tasks,
            error_handling_strategy=request.error_handling_strategy
        )
        
        # Execute pipeline
        result = validation_engine.execute_pipeline(
            validation_request,
            execution_mode=request.execution_mode
        )
        
        logger.info(
            "validation_pipeline_completed",
            request_id=result.request_id,
            total_tasks=result.total_tasks,
            successful_tasks=result.successful_tasks,
            execution_time_ms=result.total_execution_time_ms
        )
        
        # Convert result to API response
        task_results = []
        for task_result in result.task_results:
            task_results.append({
                "task_id": task_result.task_id,
                "task_type": task_result.task_type.value,
                "success": task_result.success,
                "result_data": task_result.output_data,
                "execution_time_ms": task_result.execution_time_ms,
                "quality_score": float(task_result.quality_score),
                "confidence_score": float(task_result.confidence_score),
                "errors": task_result.error_messages
            })
        
        return {
            "request_id": result.request_id,
            "overall_success": result.overall_success,
            "total_tasks": result.total_tasks,
            "successful_tasks": result.successful_tasks,
            "failed_tasks": result.failed_tasks,
            "success_rate": float(result.success_rate),
            "total_execution_time_ms": result.total_execution_time_ms,
            "average_task_time_ms": result.average_task_time_ms,
            "overall_quality_score": float(result.overall_quality_score),
            "execution_mode": result.execution_mode,
            "task_results": task_results
        }
        
    except Exception as e:
        logger.error("validation_pipeline_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Validation pipeline failed: {str(e)}")


@router.get("/engine/status", summary="Engine Status")
async def engine_status() -> Dict[str, Any]:
    """
    Get the current status and configuration of the Financial Validation Engine.
    
    Returns information about:
    - Engine readiness and health
    - Enabled modules and capabilities  
    - Performance metrics
    - Configuration details
    """
    return {
        "status": "ready" if validation_engine.is_ready else "not_ready",
        "supported_task_types": [task_type.value for task_type in validation_engine.supported_task_types],
        "configuration": {
            "tax_calculations_enabled": validation_engine.config.enable_tax_calculations,
            "business_valuations_enabled": validation_engine.config.enable_business_valuations,
            "financial_ratios_enabled": validation_engine.config.enable_financial_ratios,
            "labor_calculations_enabled": validation_engine.config.enable_labor_calculations,
            "document_parsing_enabled": validation_engine.config.enable_document_parsing,
            "precision_decimal_places": validation_engine.config.precision_decimal_places,
            "performance_timeout_seconds": validation_engine.config.performance_timeout_seconds,
            "quality_threshold": float(validation_engine.config.quality_threshold)
        },
        "health_check": {
            "timestamp": datetime.now().isoformat(),
            "memory_usage_mb": validation_engine.get_memory_usage_mb()
        }
    }