"""Italian tax and legal API endpoints."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.italian_data import ComplianceStatus, DocumentType, TaxType
from app.models.session import Session
from app.services.italian_knowledge import italian_knowledge_service

router = APIRouter()


# Request/Response Models
class TaxCalculationRequest(BaseModel):
    """Tax calculation request."""

    tax_type: TaxType
    amount: float = Field(..., gt=0, description="Amount to calculate tax on")
    tax_year: int | None = Field(default=None, description="Tax year (default: current year)")

    # VAT-specific parameters
    vat_type: str | None = Field(default="standard", description="VAT rate type")

    # IRPEF-specific parameters
    deductions: float | None = Field(default=0, ge=0, description="Total deductions")

    # Withholding tax parameters
    withholding_type: str | None = Field(default="professional", description="Type of withholding")

    @validator("tax_year")
    def validate_tax_year(self, v):
        if v is not None and (v < 2020 or v > 2030):
            raise ValueError("Tax year must be between 2020 and 2030")
        return v


class TaxCalculationResponse(BaseModel):
    """Tax calculation response."""

    calculation_id: int
    tax_type: TaxType
    base_amount: float
    tax_amount: float
    effective_rate: float
    breakdown: dict[str, Any]
    legal_reference: str
    calculation_date: datetime
    confidence_score: float


class ComplianceCheckRequest(BaseModel):
    """Document compliance check request."""

    document_type: DocumentType
    content: str = Field(..., min_length=10, description="Document content to check")
    language: str = Field(default="it", description="Document language")
    check_gdpr: bool = Field(default=True, description="Include GDPR compliance checks")


class ComplianceCheckResponse(BaseModel):
    """Compliance check response."""

    check_id: int
    document_type: DocumentType
    overall_status: ComplianceStatus
    compliance_score: float
    findings: list[dict[str, Any]]
    recommendations: list[str]
    follow_up_required: bool
    check_date: datetime


class DocumentGenerationRequest(BaseModel):
    """Document generation from template request."""

    template_code: str
    variables: dict[str, Any]
    language: str = Field(default="it", description="Document language")


class LegalSearchRequest(BaseModel):
    """Legal regulation search request."""

    keywords: list[str] = Field(..., min_items=1, description="Search keywords")
    subjects: list[str] | None = Field(default=None, description="Subject filters")
    date_from: date | None = Field(default=None, description="Regulations from date")
    limit: int = Field(default=20, le=100, description="Maximum results")


@router.post("/tax/calculate")
@limiter.limit("50 per minute")
async def calculate_tax(
    request: Request,
    tax_request: TaxCalculationRequest,
    session: Session = Depends(get_current_session),
):
    """Calculate Italian taxes (VAT, IRPEF, withholding, etc.).

    Args:
        request: FastAPI request object
        tax_request: Tax calculation parameters
        session: Current user session

    Returns:
        Tax calculation results
    """
    try:
        user_id = session.user_id

        # Convert request to dictionary for service
        calculation_request = {
            "tax_type": tax_request.tax_type.value,
            "amount": tax_request.amount,
            "tax_year": tax_request.tax_year or datetime.now().year,
        }

        # Add type-specific parameters
        if tax_request.tax_type == TaxType.VAT:
            calculation_request["vat_type"] = tax_request.vat_type
        elif tax_request.tax_type == TaxType.INCOME_TAX:
            calculation_request["deductions"] = tax_request.deductions
        elif tax_request.tax_type == TaxType.WITHHOLDING_TAX:
            calculation_request["withholding_type"] = tax_request.withholding_type

        # Perform calculation
        calculation = await italian_knowledge_service.perform_tax_calculation(
            user_id=user_id, session_id=session.id, calculation_request=calculation_request
        )

        response = TaxCalculationResponse(
            calculation_id=calculation.id,
            tax_type=calculation.calculation_type,
            base_amount=float(calculation.base_amount),
            tax_amount=float(calculation.tax_amount),
            effective_rate=float(calculation.effective_rate),
            breakdown=calculation.breakdown,
            legal_reference=calculation.breakdown.get("legal_reference", "Italian Tax Code"),
            calculation_date=calculation.calculation_date,
            confidence_score=calculation.confidence_score,
        )

        return JSONResponse(response.dict())

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "tax_calculation_api_failed",
            session_id=session.id,
            tax_type=tax_request.tax_type.value,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Tax calculation failed")


@router.get("/tax/rates")
@limiter.limit("100 per minute")
async def get_tax_rates(
    request: Request,
    tax_type: TaxType = Query(..., description="Type of tax"),
    date_ref: date | None = Query(default=None, description="Reference date"),
    session: Session = Depends(get_current_session),
):
    """Get current Italian tax rates.

    Args:
        request: FastAPI request object
        tax_type: Type of tax to get rates for
        date_ref: Reference date (default: current date)
        session: Current user session

    Returns:
        Current tax rates
    """
    try:
        rates = await italian_knowledge_service.get_tax_rates(tax_type, date_ref)

        formatted_rates = [
            {
                "id": rate.id,
                "tax_code": rate.tax_code,
                "description": rate.description,
                "rate_percentage": float(rate.rate_percentage),
                "minimum_amount": float(rate.minimum_amount) if rate.minimum_amount else None,
                "maximum_amount": float(rate.maximum_amount) if rate.maximum_amount else None,
                "valid_from": rate.valid_from.isoformat(),
                "valid_to": rate.valid_to.isoformat() if rate.valid_to else None,
                "law_reference": rate.law_reference,
                "region": rate.region,
                "municipality": rate.municipality,
            }
            for rate in rates
        ]

        return JSONResponse(
            {
                "tax_type": tax_type.value,
                "reference_date": (date_ref or date.today()).isoformat(),
                "rates": formatted_rates,
                "count": len(formatted_rates),
            }
        )

    except Exception as e:
        logger.error("tax_rates_api_failed", session_id=session.id, tax_type=tax_type.value, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve tax rates")


@router.post("/compliance/check")
@limiter.limit("20 per minute")
async def check_document_compliance(
    request: Request,
    compliance_request: ComplianceCheckRequest,
    session: Session = Depends(get_current_session),
):
    """Check document compliance with Italian regulations.

    Args:
        request: FastAPI request object
        compliance_request: Document to check
        session: Current user session

    Returns:
        Compliance check results
    """
    try:
        user_id = session.user_id

        # Convert request to dictionary for service
        document = {
            "type": compliance_request.document_type.value,
            "content": compliance_request.content,
            "language": compliance_request.language,
            "check_gdpr": compliance_request.check_gdpr,
        }

        # Perform compliance check
        check = await italian_knowledge_service.check_document_compliance(
            user_id=user_id, session_id=session.id, document=document
        )

        response = ComplianceCheckResponse(
            check_id=check.id,
            document_type=check.document_type,
            overall_status=check.overall_status,
            compliance_score=check.compliance_score,
            findings=check.findings,
            recommendations=check.recommendations,
            follow_up_required=check.follow_up_required,
            check_date=check.check_date,
        )

        return JSONResponse(response.dict())

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "compliance_check_api_failed",
            session_id=session.id,
            document_type=compliance_request.document_type.value,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Compliance check failed")


@router.post("/documents/generate")
@limiter.limit("10 per minute")
async def generate_document(
    request: Request,
    generation_request: DocumentGenerationRequest,
    session: Session = Depends(get_current_session),
):
    """Generate a legal document from template.

    Args:
        request: FastAPI request object
        generation_request: Document generation parameters
        session: Current user session

    Returns:
        Generated document
    """
    try:
        user_id = session.user_id

        # Generate document from template
        document_content = await italian_knowledge_service.generate_document_from_template(
            template_code=generation_request.template_code, variables=generation_request.variables
        )

        if not document_content:
            raise HTTPException(status_code=404, detail="Template not found or invalid")

        logger.info(
            "document_generated",
            user_id=user_id,
            template_code=generation_request.template_code,
            variables_count=len(generation_request.variables),
        )

        return JSONResponse(
            {
                "template_code": generation_request.template_code,
                "content": document_content,
                "variables_used": len(generation_request.variables),
                "language": generation_request.language,
                "generated_at": datetime.utcnow().isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "document_generation_api_failed",
            session_id=session.id,
            template_code=generation_request.template_code,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Document generation failed")


@router.get("/templates")
@limiter.limit("50 per minute")
async def list_legal_templates(
    request: Request,
    document_type: DocumentType | None = Query(default=None, description="Filter by document type"),
    category: str | None = Query(default=None, description="Filter by category"),
    limit: int = Query(default=50, le=100, description="Maximum results"),
    session: Session = Depends(get_current_session),
):
    """List available legal document templates.

    Args:
        request: FastAPI request object
        document_type: Filter by document type
        category: Filter by category
        limit: Maximum results
        session: Current user session

    Returns:
        List of available templates
    """
    try:
        # This would query the database for templates
        # Simplified implementation for now
        templates = [
            {
                "template_code": "contract_service_it",
                "document_type": "contract",
                "title": "Contratto di Prestazione di Servizi",
                "title_en": "Service Agreement Contract",
                "category": "commercial",
                "subcategory": "services",
                "description": "Standard Italian service agreement template",
                "required_fields": ["client_name", "provider_name", "service_description", "amount", "duration"],
                "valid_from": "2024-01-01",
                "version": "1.2",
            },
            {
                "template_code": "privacy_policy_gdpr_it",
                "document_type": "privacy_policy",
                "title": "Informativa Privacy GDPR",
                "title_en": "GDPR Privacy Policy",
                "category": "privacy",
                "subcategory": "gdpr",
                "description": "GDPR compliant privacy policy template",
                "required_fields": ["company_name", "data_controller", "contact_email", "legal_basis"],
                "valid_from": "2024-01-01",
                "version": "2.0",
            },
            {
                "template_code": "invoice_professional_it",
                "document_type": "invoice",
                "title": "Fattura Professionale",
                "title_en": "Professional Invoice",
                "category": "financial",
                "subcategory": "invoicing",
                "description": "Italian professional invoice template",
                "required_fields": ["client_data", "invoice_number", "date", "services", "amount", "vat"],
                "valid_from": "2024-01-01",
                "version": "1.1",
            },
        ]

        # Apply filters
        if document_type:
            templates = [t for t in templates if t["document_type"] == document_type.value]

        if category:
            templates = [t for t in templates if t["category"] == category]

        return JSONResponse(
            {
                "templates": templates[:limit],
                "total": len(templates),
                "filters": {"document_type": document_type.value if document_type else None, "category": category},
            }
        )

    except Exception as e:
        logger.error("templates_list_api_failed", session_id=session.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve templates")


@router.post("/legal/search")
@limiter.limit("30 per minute")
async def search_regulations(
    request: Request,
    search_request: LegalSearchRequest,
    session: Session = Depends(get_current_session),
):
    """Search Italian legal regulations and laws.

    Args:
        request: FastAPI request object
        search_request: Search parameters
        session: Current user session

    Returns:
        Matching regulations
    """
    try:
        regulations = await italian_knowledge_service.search_regulations(
            keywords=search_request.keywords, subjects=search_request.subjects
        )

        formatted_regulations = [
            {
                "id": reg.id,
                "type": reg.regulation_type,
                "number": reg.number,
                "year": reg.year,
                "title": reg.title,
                "summary": reg.summary,
                "authority": reg.authority,
                "enacted_date": reg.enacted_date.isoformat(),
                "effective_date": reg.effective_date.isoformat(),
                "subjects": reg.subjects,
                "source_url": reg.source_url,
                "last_verified": reg.last_verified.isoformat(),
            }
            for reg in regulations[: search_request.limit]
        ]

        return JSONResponse(
            {
                "regulations": formatted_regulations,
                "total": len(regulations),
                "search_terms": search_request.keywords,
                "subjects": search_request.subjects,
            }
        )

    except Exception as e:
        logger.error("legal_search_api_failed", session_id=session.id, keywords=search_request.keywords, error=str(e))
        raise HTTPException(status_code=500, detail="Legal search failed")


@router.get("/tax/calculator/types")
@limiter.limit("100 per minute")
async def get_calculator_types(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get available tax calculator types and their parameters.

    Args:
        request: FastAPI request object
        session: Current user session

    Returns:
        Available calculator types
    """
    try:
        calculator_types = {
            "iva": {
                "name": "IVA (VAT)",
                "description": "Italian Value Added Tax calculator",
                "parameters": {
                    "amount": {"type": "number", "required": True, "description": "Net amount before VAT"},
                    "vat_type": {
                        "type": "string",
                        "required": False,
                        "default": "standard",
                        "options": ["standard", "reduced", "super_reduced", "zero"],
                        "description": "VAT rate type",
                    },
                },
                "rates": {"standard": "22%", "reduced": "10%", "super_reduced": "4%", "zero": "0%"},
            },
            "irpef": {
                "name": "IRPEF (Personal Income Tax)",
                "description": "Italian personal income tax calculator",
                "parameters": {
                    "amount": {"type": "number", "required": True, "description": "Annual gross income"},
                    "deductions": {
                        "type": "number",
                        "required": False,
                        "default": 0,
                        "description": "Total deductions",
                    },
                },
                "brackets": [
                    {"min": 0, "max": 15000, "rate": "23%"},
                    {"min": 15001, "max": 28000, "rate": "25%"},
                    {"min": 28001, "max": 50000, "rate": "35%"},
                    {"min": 50001, "max": "∞", "rate": "43%"},
                ],
            },
            "ritenuta": {
                "name": "Ritenuta d'acconto (Withholding Tax)",
                "description": "Italian withholding tax calculator",
                "parameters": {
                    "amount": {"type": "number", "required": True, "description": "Gross amount"},
                    "withholding_type": {
                        "type": "string",
                        "required": False,
                        "default": "professional",
                        "options": ["professional", "employment", "rental", "interest", "dividends"],
                        "description": "Type of withholding",
                    },
                },
                "rates": {
                    "professional": "20%",
                    "employment": "23%",
                    "rental": "21%",
                    "interest": "26%",
                    "dividends": "26%",
                },
            },
        }

        return JSONResponse(
            {
                "calculator_types": calculator_types,
                "supported_taxes": list(calculator_types.keys()),
                "last_updated": "2024-01-01",
            }
        )

    except Exception as e:
        logger.error("calculator_types_api_failed", session_id=session.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve calculator types")


@router.get("/history/calculations")
@limiter.limit("50 per minute")
async def get_calculation_history(
    request: Request,
    tax_type: TaxType | None = Query(default=None, description="Filter by tax type"),
    limit: int = Query(default=20, le=100, description="Maximum results"),
    session: Session = Depends(get_current_session),
):
    """Get user's tax calculation history.

    Args:
        request: FastAPI request object
        tax_type: Filter by tax type
        limit: Maximum results
        session: Current user session

    Returns:
        User's calculation history
    """
    try:
        user_id = session.user_id

        # This would query the database for user's calculations
        # Simplified implementation for now
        return JSONResponse(
            {
                "calculations": [],
                "total": 0,
                "filters": {"tax_type": tax_type.value if tax_type else None, "user_id": user_id},
                "message": "Calculation history feature will be implemented with database integration",
            }
        )

    except Exception as e:
        logger.error("calculation_history_api_failed", session_id=session.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve calculation history")


@router.get("/compliance/history")
@limiter.limit("50 per minute")
async def get_compliance_history(
    request: Request,
    document_type: DocumentType | None = Query(default=None, description="Filter by document type"),
    status: ComplianceStatus | None = Query(default=None, description="Filter by compliance status"),
    limit: int = Query(default=20, le=100, description="Maximum results"),
    session: Session = Depends(get_current_session),
):
    """Get user's compliance check history.

    Args:
        request: FastAPI request object
        document_type: Filter by document type
        status: Filter by compliance status
        limit: Maximum results
        session: Current user session

    Returns:
        User's compliance check history
    """
    try:
        user_id = session.user_id

        # This would query the database for user's compliance checks
        # Simplified implementation for now
        return JSONResponse(
            {
                "checks": [],
                "total": 0,
                "filters": {
                    "document_type": document_type.value if document_type else None,
                    "status": status.value if status else None,
                    "user_id": user_id,
                },
                "message": "Compliance history feature will be implemented with database integration",
            }
        )

    except Exception as e:
        logger.error("compliance_history_api_failed", session_id=session.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance history")
