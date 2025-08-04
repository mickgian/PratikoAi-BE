"""Italian tax and legal data models."""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlmodel import Field, SQLModel, Column, JSON
from sqlalchemy import Index, Text


class TaxType(str, Enum):
    """Italian tax types."""
    VAT = "iva"  # IVA (Imposta sul Valore Aggiunto)
    INCOME_TAX = "irpef"  # IRPEF (Imposta sul Reddito delle Persone Fisiche)
    CORPORATE_TAX = "ires"  # IRES (Imposta sul Reddito delle Società)
    WITHHOLDING_TAX = "ritenuta"  # Ritenuta d'acconto
    REGIONAL_TAX = "irap"  # IRAP (Imposta Regionale sulle Attività Produttive)
    PROPERTY_TAX = "imu"  # IMU (Imposta Municipale Unica)
    STAMP_DUTY = "bollo"  # Imposta di bollo


class DocumentType(str, Enum):
    """Italian legal document types."""
    CONTRACT = "contratto"
    INVOICE = "fattura"
    RECEIPT = "ricevuta"
    DECLARATION = "dichiarazione"
    FORM = "modulo"
    POWER_OF_ATTORNEY = "procura"
    ARTICLES_OF_ASSOCIATION = "statuto"
    PRIVACY_POLICY = "privacy_policy"
    TERMS_CONDITIONS = "termini_condizioni"


class ComplianceStatus(str, Enum):
    """Compliance check status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    NEEDS_REVIEW = "needs_review"
    UNKNOWN = "unknown"


class ItalianTaxRate(SQLModel, table=True):
    """Italian tax rates and regulations."""
    
    __tablename__ = "italian_tax_rates"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Tax identification
    tax_type: TaxType = Field(..., description="Type of tax")
    tax_code: str = Field(..., description="Official tax code")
    description: str = Field(..., description="Tax description in Italian")
    description_en: Optional[str] = Field(default=None, description="Tax description in English")
    
    # Rate information
    rate_percentage: Decimal = Field(..., description="Tax rate as percentage")
    minimum_amount: Optional[Decimal] = Field(default=None, description="Minimum taxable amount")
    maximum_amount: Optional[Decimal] = Field(default=None, description="Maximum taxable amount")
    
    # Validity period
    valid_from: date = Field(..., description="Rate valid from date")
    valid_to: Optional[date] = Field(default=None, description="Rate valid until date")
    
    # Legal references
    law_reference: str = Field(..., description="Legal reference (law, decree, etc.)")
    article_reference: Optional[str] = Field(default=None, description="Specific article reference")
    
    # Geographic scope
    region: Optional[str] = Field(default=None, description="Region if regionally specific")
    municipality: Optional[str] = Field(default=None, description="Municipality if locally specific")
    
    # Additional data
    conditions: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    exemptions: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_tax_rate_type", "tax_type"),
        Index("idx_tax_rate_code", "tax_code"),
        Index("idx_tax_rate_validity", "valid_from", "valid_to"),
        Index("idx_tax_rate_location", "region", "municipality"),
    )


class ItalianLegalTemplate(SQLModel, table=True):
    """Italian legal document templates."""
    
    __tablename__ = "italian_legal_templates"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Template identification
    template_code: str = Field(..., unique=True, description="Unique template code")
    document_type: DocumentType = Field(..., description="Type of legal document")
    title: str = Field(..., description="Template title in Italian")
    title_en: Optional[str] = Field(default=None, description="Template title in English")
    
    # Template content
    content: str = Field(..., sa_column=Column(Text), description="Template content with placeholders")
    variables: Dict[str, Any] = Field(..., sa_column=Column(JSON), description="Template variables definition")
    
    # Legal information
    legal_basis: str = Field(..., description="Legal basis for the document")
    required_fields: List[str] = Field(..., sa_column=Column(JSON), description="Required fields for validity")
    optional_fields: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Optional fields")
    
    # Usage information
    category: str = Field(..., description="Document category")
    subcategory: Optional[str] = Field(default=None, description="Document subcategory")
    industry_specific: Optional[str] = Field(default=None, description="Industry if specific")
    
    # Validity and compliance
    valid_from: date = Field(..., description="Template valid from date")
    valid_to: Optional[date] = Field(default=None, description="Template valid until date")
    compliance_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Metadata
    version: str = Field(default="1.0", description="Template version")
    author: str = Field(..., description="Template author/source")
    review_date: Optional[date] = Field(default=None, description="Last review date")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_template_code", "template_code"),
        Index("idx_template_type", "document_type"),
        Index("idx_template_category", "category", "subcategory"),
        Index("idx_template_validity", "valid_from", "valid_to"),
        Index("idx_template_industry", "industry_specific"),
    )


class ItalianRegulation(SQLModel, table=True):
    """Italian regulations and legal sources."""
    
    __tablename__ = "italian_regulations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Regulation identification
    regulation_type: str = Field(..., description="Type (law, decree, regulation, etc.)")
    number: str = Field(..., description="Regulation number")
    year: int = Field(..., description="Year of enactment")
    title: str = Field(..., sa_column=Column(Text), description="Official title")
    
    # Content
    summary: str = Field(..., sa_column=Column(Text), description="Regulation summary")
    full_text_url: Optional[str] = Field(default=None, description="URL to full text")
    
    # Legal hierarchy
    authority: str = Field(..., description="Issuing authority")
    jurisdiction: str = Field(default="national", description="Jurisdiction level")
    
    # Dates
    enacted_date: date = Field(..., description="Date of enactment")
    effective_date: date = Field(..., description="Date when regulation becomes effective")
    repealed_date: Optional[date] = Field(default=None, description="Date when regulation was repealed")
    
    # Relationships
    amends: Optional[List[int]] = Field(default_factory=list, sa_column=Column(JSON), description="IDs of regulations this amends")
    amended_by: Optional[List[int]] = Field(default_factory=list, sa_column=Column(JSON), description="IDs of regulations that amend this")
    
    # Subject matter
    subjects: List[str] = Field(..., sa_column=Column(JSON), description="Subject matter tags")
    keywords: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Search keywords")
    
    # Source tracking
    source_url: str = Field(..., description="Official source URL")
    last_verified: datetime = Field(default_factory=datetime.utcnow, description="Last verification date")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_regulation_type_number", "regulation_type", "number", "year"),
        Index("idx_regulation_authority", "authority"),
        Index("idx_regulation_dates", "enacted_date", "effective_date"),
        Index("idx_regulation_subjects", "subjects"),
        Index("idx_regulation_status", "repealed_date"),
    )


class TaxCalculation(SQLModel, table=True):
    """Tax calculation records and results."""
    
    __tablename__ = "tax_calculations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Calculation identification
    user_id: str = Field(..., description="User who performed calculation")
    session_id: str = Field(..., description="Session ID")
    calculation_type: TaxType = Field(..., description="Type of tax calculated")
    
    # Input parameters
    base_amount: Decimal = Field(..., description="Base amount for calculation")
    tax_year: int = Field(..., description="Tax year")
    input_parameters: Dict[str, Any] = Field(..., sa_column=Column(JSON), description="All input parameters")
    
    # Results
    tax_amount: Decimal = Field(..., description="Calculated tax amount")
    effective_rate: Decimal = Field(..., description="Effective tax rate applied")
    breakdown: Dict[str, Any] = Field(..., sa_column=Column(JSON), description="Detailed calculation breakdown")
    
    # Legal references used
    regulations_used: List[int] = Field(..., sa_column=Column(JSON), description="Regulation IDs used in calculation")
    tax_rates_used: List[int] = Field(..., sa_column=Column(JSON), description="Tax rate IDs used")
    
    # Metadata
    calculation_date: datetime = Field(default_factory=datetime.utcnow)
    calculation_method: str = Field(..., description="Method/algorithm used")
    confidence_score: float = Field(default=1.0, description="Confidence in calculation accuracy")
    
    # Audit trail
    reviewed_by: Optional[str] = Field(default=None, description="Professional who reviewed calculation")
    review_date: Optional[datetime] = Field(default=None, description="Review timestamp")
    review_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    __table_args__ = (
        Index("idx_tax_calc_user", "user_id"),
        Index("idx_tax_calc_session", "session_id"),
        Index("idx_tax_calc_type", "calculation_type"),
        Index("idx_tax_calc_date", "calculation_date"),
        Index("idx_tax_calc_year", "tax_year"),
    )


class ComplianceCheck(SQLModel, table=True):
    """Compliance check results and records."""
    
    __tablename__ = "compliance_checks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Check identification
    user_id: str = Field(..., description="User who requested check")
    session_id: str = Field(..., description="Session ID")
    check_type: str = Field(..., description="Type of compliance check")
    
    # Document/data being checked
    document_type: Optional[DocumentType] = Field(default=None, description="Type of document checked")
    document_content: Optional[str] = Field(default=None, sa_column=Column(Text), description="Document content")
    check_parameters: Dict[str, Any] = Field(..., sa_column=Column(JSON), description="Check parameters")
    
    # Results
    overall_status: ComplianceStatus = Field(..., description="Overall compliance status")
    compliance_score: float = Field(..., description="Compliance score (0-1)")
    
    # Detailed findings
    findings: List[Dict[str, Any]] = Field(..., sa_column=Column(JSON), description="Detailed compliance findings")
    recommendations: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Improvement recommendations")
    
    # Legal references
    regulations_checked: List[int] = Field(..., sa_column=Column(JSON), description="Regulation IDs checked against")
    citations: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON), description="Legal citations")
    
    # Metadata
    check_date: datetime = Field(default_factory=datetime.utcnow)
    check_method: str = Field(..., description="Compliance check method used")
    
    # Follow-up
    follow_up_required: bool = Field(default=False, description="Whether follow-up is required")
    follow_up_date: Optional[datetime] = Field(default=None, description="Next check date")
    
    __table_args__ = (
        Index("idx_compliance_user", "user_id"),
        Index("idx_compliance_session", "session_id"),
        Index("idx_compliance_type", "check_type"),
        Index("idx_compliance_status", "overall_status"),
        Index("idx_compliance_date", "check_date"),
        Index("idx_compliance_followup", "follow_up_required", "follow_up_date"),
    )


class DocumentCategory(str, Enum):
    """Italian document categories from official sources."""
    CIRCOLARE = "circolare"  # Circolari
    RISOLUZIONE = "risoluzione"  # Risoluzioni
    PROVVEDIMENTO = "provvedimento"  # Provvedimenti
    DECRETO = "decreto"  # Decreti
    LEGGE = "legge"  # Leggi
    MESSAGGIO = "messaggio"  # Messaggi INPS
    COMUNICATO = "comunicato"  # Comunicati stampa
    ALTRO = "altro"  # Altri documenti


class ItalianOfficialDocument(SQLModel, table=True):
    """Official Italian government documents collected from RSS feeds."""
    
    __tablename__ = "italian_official_documents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Document identification
    document_id: str = Field(..., unique=True, description="Unique document identifier")
    title: str = Field(..., description="Document title")
    category: DocumentCategory = Field(..., description="Document category")
    
    # Source information
    authority: str = Field(..., description="Issuing authority (Agenzia Entrate, INPS, etc.)")
    source_url: str = Field(..., description="Original document URL")
    rss_feed: str = Field(..., description="RSS feed where document was found")
    
    # Content
    summary: Optional[str] = Field(default=None, sa_column=Column(Text), description="Document summary")
    full_content: Optional[str] = Field(default=None, sa_column=Column(Text), description="Full document content")
    content_hash: str = Field(..., description="Content hash for duplicate detection")
    
    # Dates
    publication_date: datetime = Field(..., description="Official publication date")
    effective_date: Optional[datetime] = Field(default=None, description="When document becomes effective")
    expiry_date: Optional[datetime] = Field(default=None, description="Document expiry date if applicable")
    
    # Classification
    tax_types: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Related tax types")
    keywords: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Extracted keywords")
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Classification tags")
    
    # Processing status
    processing_status: str = Field(default="pending", description="Processing status")
    indexed_at: Optional[datetime] = Field(default=None, description="When document was indexed")
    vector_id: Optional[str] = Field(default=None, description="Vector database ID")
    
    # Metadata
    file_type: Optional[str] = Field(default=None, description="Document file type (PDF, HTML, etc.)")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    language: str = Field(default="it", description="Document language")
    
    # Collection metadata
    collected_at: datetime = Field(default_factory=datetime.utcnow, description="When document was collected")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
    __table_args__ = (
        Index("idx_doc_id", "document_id"),
        Index("idx_doc_authority", "authority"),
        Index("idx_doc_category", "category"),
        Index("idx_doc_pub_date", "publication_date"),
        Index("idx_doc_status", "processing_status"),
        Index("idx_doc_hash", "content_hash"),
        Index("idx_doc_collection_date", "collected_at"),
    )


class ItalianKnowledgeSource(SQLModel, table=True):
    """Sources of Italian legal and tax knowledge."""
    
    __tablename__ = "italian_knowledge_sources"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Source identification
    source_name: str = Field(..., description="Source name")
    source_type: str = Field(..., description="Type (official, academic, professional, etc.)")
    authority: str = Field(..., description="Issuing authority/organization")
    
    # Access information
    base_url: str = Field(..., description="Base URL for the source")
    rss_url: Optional[str] = Field(default=None, description="RSS feed URL")
    api_endpoint: Optional[str] = Field(default=None, description="API endpoint if available")
    api_key_required: bool = Field(default=False, description="Whether API key is required")
    
    # Content information
    content_types: List[str] = Field(..., sa_column=Column(JSON), description="Types of content available")
    update_frequency: str = Field(..., description="How often content is updated")
    language: str = Field(default="it", description="Primary language")
    
    # Technical details
    data_format: str = Field(..., description="Data format (JSON, XML, HTML, etc.)")
    rate_limit: Optional[str] = Field(default=None, description="API rate limits")
    
    # Quality and reliability
    reliability_score: float = Field(default=1.0, description="Source reliability score (0-1)")
    last_accessed: datetime = Field(default_factory=datetime.utcnow, description="Last successful access")
    last_document_date: Optional[datetime] = Field(default=None, description="Date of most recent document")
    access_status: str = Field(default="active", description="Current access status")
    
    # Usage tracking
    usage_count: int = Field(default=0, description="Number of times accessed")
    success_rate: float = Field(default=1.0, description="Success rate of API calls")
    documents_collected: int = Field(default=0, description="Total documents collected")
    
    # Metadata
    description: str = Field(..., sa_column=Column(Text), description="Source description")
    contact_info: Optional[str] = Field(default=None, description="Contact information")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_source_name", "source_name"),
        Index("idx_source_type", "source_type"),
        Index("idx_source_authority", "authority"),
        Index("idx_source_status", "access_status"),
        Index("idx_source_reliability", "reliability_score"),
    )