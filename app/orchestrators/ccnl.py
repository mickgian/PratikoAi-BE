# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs): return None
    def rag_step_timer(*args, **kwargs): return nullcontext()

async def step_81__ccnlquery(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements
    ID: RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements
    Type: process | Category: ccnl | Node: CCNLQuery

    Thin async orchestrator that executes on-demand CCNL (Italian Collective Labor Agreement) queries
    when the LLM calls the CCNLTool. Uses CCNLTool for querying labor agreements, salary calculations,
    leave entitlements, and compliance information. Routes to Step 99 (ToolResults).
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(81, 'RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements', 'CCNLQuery',
                       request_id=request_id, stage="start"):
        rag_step_log(step=81, step_id='RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements', node_label='CCNLQuery',
                     category='ccnl', type='process', request_id=request_id, processing_stage="started")

        # Extract tool arguments
        tool_args = ctx.get('tool_args', {})
        tool_call_id = ctx.get('tool_call_id')
        query_type = tool_args.get('query_type', 'search')

        # Execute CCNL query using CCNLTool
        try:
            from app.core.langgraph.tools.ccnl_tool import ccnl_tool

            # Call the CCNLTool with the arguments
            ccnl_response = await ccnl_tool._arun(**tool_args)

            # Parse the JSON response
            import json
            try:
                ccnl_result = json.loads(ccnl_response) if isinstance(ccnl_response, str) else ccnl_response
            except (json.JSONDecodeError, TypeError):
                ccnl_result = {'success': False, 'error': 'Failed to parse CCNL response', 'raw_response': str(ccnl_response)}

            success = ccnl_result.get('success', False)

            rag_step_log(
                step=81,
                step_id='RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements',
                node_label='CCNLQuery',
                request_id=request_id,
                query_type=query_type,
                sector=tool_args.get('sector'),
                success=success,
                processing_stage="completed"
            )

        except Exception as e:
            rag_step_log(
                step=81,
                step_id='RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements',
                node_label='CCNLQuery',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            ccnl_result = {
                'success': False,
                'error': str(e),
                'message': 'Si è verificato un errore durante la query CCNL.'
            }

        # Build result with preserved context
        result = {
            **ctx,
            'ccnl_results': ccnl_result,
            'query_result': ccnl_result,  # Alias for compatibility
            'query_type': query_type,
            'sector': tool_args.get('sector'),
            'query_metadata': {
                'query_type': query_type,
                'sector': tool_args.get('sector'),
                'job_category': tool_args.get('job_category'),
                'tool_call_id': tool_call_id
            },
            'tool_call_id': tool_call_id,
            'next_step': 'tool_results',  # Routes to Step 99 per Mermaid (CCNLQuery → PostgresQuery → CCNLCalc → ToolResults, but collapsed)
            'request_id': request_id
        }

        return result

async def step_100__ccnlcalc(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 100 — CCNLCalculator.calculate Perform calculations

    ID: RAG.ccnl.ccnlcalculator.calculate.perform.calculations
    Type: process | Category: ccnl | Node: CCNLCalc

    Thin async orchestrator that performs CCNL calculations using the enhanced calculation engine.
    Receives CCNL agreement data and calculation parameters from PostgresQuery (Step 97),
    delegates to EnhancedCCNLCalculator for comprehensive compensation calculations,
    and routes results to ToolResults (Step 99) per Mermaid diagram.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(100, 'RAG.ccnl.ccnlcalculator.calculate.perform.calculations', 'CCNLCalc',
                       request_id=request_id, stage="start"):
        rag_step_log(step=100, step_id='RAG.ccnl.ccnlcalculator.calculate.perform.calculations', node_label='CCNLCalc',
                     category='ccnl', type='process', request_id=request_id, processing_stage="started")

        try:
            # Perform CCNL calculations using helper function
            calculation_result = await _perform_ccnl_calculations(ctx)

            # Build result with preserved context and calculation outputs
            result = {
                **ctx,
                'compensation_breakdown': calculation_result['compensation_breakdown'],
                'calculation_success': calculation_result['success'],
                'calculation_metadata': calculation_result['metadata'],
                'tool_result_data': calculation_result['tool_result_data'],
                'previous_step': ctx.get('rag_step'),
                'rag_step': 100,
                'next_step': 99,  # Route to ToolResults per Mermaid
                'next_step_id': 'RAG.platform.return.to.tool.caller',
                'request_id': request_id
            }

            # Add error context if calculation failed
            if not calculation_result['success']:
                result['error'] = calculation_result.get('error', 'CCNL calculation failed')

            rag_step_log(
                step=100,
                step_id='RAG.ccnl.ccnlcalculator.calculate.perform.calculations',
                node_label='CCNLCalc',
                request_id=request_id,
                calculation_success=calculation_result['success'],
                gross_total=str(calculation_result['compensation_breakdown'].get('gross_total', '0.00')) if calculation_result['success'] else None,
                net_total=str(calculation_result['compensation_breakdown'].get('net_total', '0.00')) if calculation_result['success'] else None,
                processing_stage="completed"
            )

            return result

        except Exception as e:
            rag_step_log(
                step=100,
                step_id='RAG.ccnl.ccnlcalculator.calculate.perform.calculations',
                node_label='CCNLCalc',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            # On error, return failure context for ToolResults step
            return await _handle_ccnl_calculation_error(ctx, str(e))


async def _perform_ccnl_calculations(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Perform CCNL calculations using the enhanced calculation engine.

    Delegates to EnhancedCCNLCalculator with proper error handling and result formatting.
    """
    try:
        # Extract CCNL agreement and calculation parameters from context
        ccnl_agreement_data = ctx.get('ccnl_agreement')
        if not ccnl_agreement_data:
            return {
                'success': False,
                'error': 'Missing CCNL agreement data',
                'compensation_breakdown': {},
                'metadata': {'error': 'No CCNL agreement found in context'},
                'tool_result_data': {
                    'tool_type': 'CCNL',
                    'success': False,
                    'error': 'Missing CCNL agreement data',
                    'tool_call_id': ctx.get('tool_call', {}).get('id')
                }
            }

        calculation_params = ctx.get('calculation_params', {})
        if not calculation_params:
            return {
                'success': False,
                'error': 'Missing calculation parameters',
                'compensation_breakdown': {},
                'metadata': {'error': 'No calculation parameters provided'},
                'tool_result_data': {
                    'tool_type': 'CCNL',
                    'success': False,
                    'error': 'Missing calculation parameters',
                    'tool_call_id': ctx.get('tool_call', {}).get('id')
                }
            }

        # Import required classes for calculation
        from app.models.ccnl_data import CCNLAgreement, CCNLSector, GeographicArea, CompanySize
        from app.services.ccnl_calculator_engine import EnhancedCCNLCalculator, CalculationPeriod
        from datetime import date

        # Create minimal CCNL agreement object with required fields
        sector_name = ccnl_agreement_data.get('sector', 'COMMERCIO_TERZIARIO')
        if sector_name == 'COMMERCIO':
            sector_name = 'COMMERCIO_TERZIARIO'  # Map generic COMMERCIO to specific enum value

        ccnl = CCNLAgreement(
            sector=CCNLSector(sector_name.lower()),  # Enum values are lowercase
            name=ccnl_agreement_data.get('name', 'Generic CCNL'),
            valid_from=date.fromisoformat(ccnl_agreement_data.get('valid_from', '2024-01-01'))
        )

        # Initialize enhanced calculator
        calculator = EnhancedCCNLCalculator(ccnl)

        # Extract parameters with defaults
        level_code = calculation_params.get('level_code')
        if not level_code:
            return {
                'success': False,
                'error': 'Missing required level_code parameter',
                'compensation_breakdown': {},
                'metadata': {'error': 'level_code is required for calculations'},
                'tool_result_data': {
                    'tool_type': 'CCNL',
                    'success': False,
                    'error': 'Missing level_code parameter',
                    'tool_call_id': ctx.get('tool_call', {}).get('id')
                }
            }

        # Apply parameter defaults
        seniority_months = calculation_params.get('seniority_months', 0)
        geographic_area = _parse_geographic_area(calculation_params.get('geographic_area', 'NAZIONALE'))
        company_size = _parse_company_size(calculation_params.get('company_size'))
        working_days_per_month = calculation_params.get('working_days_per_month', 22)
        overtime_hours_monthly = calculation_params.get('overtime_hours_monthly', 0)
        include_allowances = calculation_params.get('include_allowances', True)
        period = _parse_calculation_period(calculation_params.get('period', 'ANNUAL'))

        # Perform calculation
        compensation_breakdown = calculator.calculate_comprehensive_compensation(
            level_code=level_code,
            seniority_months=seniority_months,
            geographic_area=geographic_area,
            company_size=company_size,
            working_days_per_month=working_days_per_month,
            overtime_hours_monthly=overtime_hours_monthly,
            include_allowances=include_allowances,
            period=period
        )

        # Format results for context passing
        breakdown_dict = _format_compensation_breakdown(compensation_breakdown)

        return {
            'success': True,
            'compensation_breakdown': breakdown_dict,
            'metadata': {
                'calculation_engine': 'EnhancedCCNLCalculator',
                'level_code': level_code,
                'geographic_area': str(geographic_area),
                'company_size': str(company_size) if company_size else None,
                'period': str(period),
                'calculation_timestamp': ctx.get('request_id', 'unknown')
            },
            'tool_result_data': {
                'tool_type': 'CCNL',
                'tool_call_id': ctx.get('tool_call', {}).get('id'),
                'success': True,
                'calculation_complete': True,
                'calculation_result': {
                    'level_code': level_code,
                    'gross_annual': str(breakdown_dict.get('gross_total', '0.00')),
                    'net_annual': str(breakdown_dict.get('net_total', '0.00')),
                    'breakdown': breakdown_dict
                }
            }
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Calculation engine error: {str(e)}',
            'compensation_breakdown': {},
            'metadata': {'exception': str(e)},
            'tool_result_data': {
                'tool_type': 'CCNL',
                'success': False,
                'error': f'Calculation failed: {str(e)}',
                'tool_call_id': ctx.get('tool_call', {}).get('id')
            }
        }


def _format_compensation_breakdown(breakdown) -> Dict[str, Any]:
    """Format compensation breakdown for JSON serialization."""
    return {
        'base_salary': breakdown.base_salary,
        'thirteenth_month': breakdown.thirteenth_month,
        'fourteenth_month': breakdown.fourteenth_month,
        'overtime': breakdown.overtime,
        'allowances': dict(breakdown.allowances) if hasattr(breakdown.allowances, 'items') else breakdown.allowances,
        'deductions': dict(breakdown.deductions) if hasattr(breakdown.deductions, 'items') else breakdown.deductions,
        'gross_total': breakdown.gross_total,
        'net_total': breakdown.net_total,
        'period': str(breakdown.period)
    }


def _parse_geographic_area(area_str: str):
    """Parse geographic area string to enum."""
    from app.models.ccnl_data import GeographicArea
    area_mapping = {
        'NAZIONALE': GeographicArea.NAZIONALE,
        'NORD': GeographicArea.NORD,
        'CENTRO': GeographicArea.CENTRO,
        'SUD': GeographicArea.SUD,
        'SUD_ISOLE': GeographicArea.SUD_ISOLE,
        'SICILIA': GeographicArea.SUD_ISOLE,  # Sicily maps to SUD_ISOLE
        'SARDEGNA': GeographicArea.SUD_ISOLE  # Sardinia maps to SUD_ISOLE
    }
    return area_mapping.get(area_str.upper(), GeographicArea.NAZIONALE)


def _parse_company_size(size_str: Optional[str]):
    """Parse company size string to enum."""
    if not size_str:
        return None

    from app.models.ccnl_data import CompanySize
    size_mapping = {
        'MICRO': CompanySize.MICRO,
        'SMALL': CompanySize.SMALL,
        'MEDIUM': CompanySize.MEDIUM,
        'LARGE': CompanySize.LARGE,
        'EXTRA_LARGE': CompanySize.LARGE  # Map EXTRA_LARGE to LARGE
    }
    return size_mapping.get(size_str.upper())


def _parse_calculation_period(period_str: str):
    """Parse calculation period string to enum."""
    from app.services.ccnl_calculator_engine import CalculationPeriod
    period_mapping = {
        'DAILY': CalculationPeriod.DAILY,
        'WEEKLY': CalculationPeriod.WEEKLY,
        'MONTHLY': CalculationPeriod.MONTHLY,
        'QUARTERLY': CalculationPeriod.QUARTERLY,
        'ANNUAL': CalculationPeriod.ANNUAL
    }
    return period_mapping.get(period_str.upper(), CalculationPeriod.ANNUAL)


async def _handle_ccnl_calculation_error(ctx: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
    """Handle errors in CCNL calculation with graceful fallback."""
    return {
        **ctx,
        'calculation_success': False,
        'error': error_msg,
        'compensation_breakdown': {},
        'calculation_metadata': {
            'error': error_msg,
            'fallback_applied': True,
            'calculation_failed': True
        },
        'tool_result_data': {
            'tool_type': 'CCNL',
            'success': False,
            'error': error_msg,
            'tool_call_id': ctx.get('tool_call', {}).get('id')
        },
        'previous_step': ctx.get('rag_step'),
        'rag_step': 100,
        'next_step': 99,  # Still route to ToolResults for error handling
        'next_step_id': 'RAG.platform.return.to.tool.caller',
        'request_id': ctx.get('request_id', 'unknown')
    }
