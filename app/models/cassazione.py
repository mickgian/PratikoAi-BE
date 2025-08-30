"""
Cassazione (Italian Supreme Court) Data Models.

This module defines the data models for Italian Supreme Court decisions,
jurisprudence, and legal precedents related to labor law and CCNL matters.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel as PydanticBaseModel, Field, validator
from sqlmodel import SQLModel, Field as SQLField, Column, Text, JSON
import uuid

from app.models.base import BaseModel
from app.models.ccnl_data import CCNLSector


class CassazioneSection(str, Enum):
    """Sections of the Italian Supreme Court (Cassazione)."""
    CIVILE_LAVORO = "civile_lavoro"  # Civil Labor Section
    CIVILE_PRIMA = "civile_prima"    # First Civil Section
    CIVILE_SECONDA = "civile_seconda"  # Second Civil Section
    CIVILE_TERZA = "civile_terza"    # Third Civil Section
    PENALE_PRIMA = "penale_prima"    # First Criminal Section
    PENALE_SECONDA = "penale_seconda"  # Second Criminal Section
    SEZIONI_UNITE_CIVILI = "sezioni_unite_civili"  # United Civil Sections
    SEZIONI_UNITE_PENALI = "sezioni_unite_penali"  # United Criminal Sections


class DecisionType(str, Enum):
    """Types of Cassazione decisions."""
    SENTENZA = "sentenza"  # Judgment
    ORDINANZA = "ordinanza"  # Order
    DECRETO = "decreto"  # Decree
    MASSIMA = "massima"  # Legal principle/maxim
    ORIENTAMENTO = "orientamento"  # Orientation/trend


class LegalPrincipleArea(str, Enum):
    """Legal principle areas for labor law."""
    CONTRATTO_LAVORO = "contratto_lavoro"  # Employment contract
    CCNL_INTERPRETAZIONE = "ccnl_interpretazione"  # CCNL interpretation
    LICENZIAMENTO = "licenziamento"  # Dismissal
    RETRIBUZIONE = "retribuzione"  # Remuneration
    ORARIO_LAVORO = "orario_lavoro"  # Working time
    FERIE_PERMESSI = "ferie_permessi"  # Holidays and leave
    CONTRIBUTI_PREVIDENZA = "contributi_previdenza"  # Social security contributions
    SICUREZZA_LAVORO = "sicurezza_lavoro"  # Workplace safety
    DISCRIMINAZIONE = "discriminazione"  # Discrimination
    SINDACATO = "sindacato"  # Trade unions
    SCIOPERO = "sciopero"  # Strike action
    MATERNITA_PATERNITA = "maternita_paternita"  # Maternity/paternity
    MALATTIA_INFORTUNIO = "malattia_infortunio"  # Illness/injury


class CassazioneDecision(BaseModel, table=True):
    """
    Model for Italian Supreme Court (Cassazione) decisions.
    
    Represents a court decision with full legal details, precedent value,
    and relationships to CCNL sectors and legal principles.
    """
    __tablename__ = "cassazione_decisions"

    # Primary key
    id: Optional[int] = SQLField(default=None, primary_key=True)

    # Basic decision information
    decision_id: str = SQLField(max_length=50, unique=True, index=True)
    decision_number: int
    decision_year: int
    section: CassazioneSection
    decision_type: DecisionType = DecisionType.SENTENZA
    
    # Dates
    decision_date: date
    publication_date: Optional[date] = None
    filing_date: Optional[date] = None
    
    # Content
    title: str = SQLField(max_length=500)
    summary: Optional[str] = SQLField(sa_column=Column(Text))
    full_text: Optional[str] = SQLField(sa_column=Column(Text))
    legal_principle: Optional[str] = SQLField(sa_column=Column(Text))
    keywords: Optional[List[str]] = SQLField(sa_column=Column(JSON))
    
    # Classification
    legal_areas: Optional[List[str]] = SQLField(sa_column=Column(JSON))
    related_sectors: Optional[List[str]] = SQLField(sa_column=Column(JSON))
    precedent_value: str = SQLField(max_length=20, default="medium")
    
    # References and citations
    cited_decisions: Optional[List[str]] = SQLField(sa_column=Column(JSON))
    citing_decisions: Optional[List[str]] = SQLField(sa_column=Column(JSON))
    related_laws: Optional[List[str]] = SQLField(sa_column=Column(JSON))
    related_ccnl: Optional[List[str]] = SQLField(sa_column=Column(JSON))
    
    # Parties and case details
    appellant: Optional[str] = SQLField(max_length=200)
    respondent: Optional[str] = SQLField(max_length=200)
    case_subject: Optional[str] = SQLField(sa_column=Column(Text))
    court_of_origin: Optional[str] = SQLField(max_length=200)
    
    # Decision outcome
    outcome: Optional[str] = SQLField(max_length=50)
    damages_awarded: Optional[str] = SQLField(max_length=100)
    
    # Metadata
    source_url: Optional[str] = SQLField(max_length=500)
    confidence_score: int = 95


class CassazioneLegalPrinciple(PydanticBaseModel):
    """
    Pydantic model for extracted legal principles from Cassazione decisions.
    
    Represents a legal principle or precedent that can be applied to
    similar cases and CCNL interpretation issues.
    """
    principle_id: str = Field(..., description="Unique identifier for the legal principle")
    decision_id: str = Field(..., description="Source decision ID")
    title: str = Field(..., description="Brief title of the legal principle")
    principle_text: str = Field(..., description="Full text of the legal principle")
    legal_area: LegalPrincipleArea = Field(..., description="Area of law")
    related_sectors: List[CCNLSector] = Field(default_factory=list, description="Applicable CCNL sectors")
    precedent_strength: str = Field("medium", description="Strength of precedent (high/medium/low)")
    decision_date: date = Field(..., description="Date of the source decision")
    keywords: List[str] = Field(default_factory=list, description="Legal keywords")
    related_principles: List[str] = Field(default_factory=list, description="Related principle IDs")


class CassazioneSearchQuery(PydanticBaseModel):
    """
    Search query model for Cassazione database searches.
    
    Allows complex searches across decisions, legal principles,
    and jurisprudence with filtering by multiple criteria.
    """
    keywords: Optional[List[str]] = Field(None, description="Keywords to search for")
    legal_areas: Optional[List[LegalPrincipleArea]] = Field(None, description="Legal principle areas")
    sectors: Optional[List[CCNLSector]] = Field(None, description="Related CCNL sectors")
    sections: Optional[List[CassazioneSection]] = Field(None, description="Court sections")
    decision_types: Optional[List[DecisionType]] = Field(None, description="Types of decisions")
    date_from: Optional[date] = Field(None, description="Start date for decisions")
    date_to: Optional[date] = Field(None, description="End date for decisions")
    precedent_value: Optional[str] = Field(None, description="Minimum precedent value (high/medium/low)")
    decision_numbers: Optional[List[int]] = Field(None, description="Specific decision numbers")
    full_text_search: Optional[str] = Field(None, description="Full text search query")
    max_results: int = Field(50, ge=1, le=500, description="Maximum number of results")
    include_full_text: bool = Field(False, description="Include full decision text")
    sort_by: str = Field("decision_date", description="Sort field (decision_date, precedent_value, relevance)")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")


class CassazioneSearchResult(PydanticBaseModel):
    """
    Search result model for Cassazione queries.
    
    Provides comprehensive search results with relevance scoring,
    legal principle extraction, and related decision suggestions.
    """
    decision_id: str
    decision_number: int
    decision_year: int
    section: CassazioneSection
    decision_type: DecisionType
    decision_date: date
    title: str
    summary: Optional[str] = None
    legal_principle: Optional[str] = None
    legal_areas: List[LegalPrincipleArea] = Field(default_factory=list)
    related_sectors: List[CCNLSector] = Field(default_factory=list)
    precedent_value: str
    keywords: List[str] = Field(default_factory=list)
    relevance_score: float = Field(0.0, description="Search relevance score (0-1)")
    full_text: Optional[str] = None
    source_url: Optional[str] = None


class CassazioneJurisprudenceAnalysis(PydanticBaseModel):
    """
    Model for jurisprudence analysis and trend identification.
    
    Provides analysis of legal trends, principle evolution,
    and consistency in court decisions over time.
    """
    analysis_id: str = Field(..., description="Unique analysis identifier")
    analysis_date: datetime = Field(default_factory=datetime.utcnow, description="Analysis creation date")
    legal_area: LegalPrincipleArea = Field(..., description="Area of law analyzed")
    related_sectors: List[CCNLSector] = Field(default_factory=list, description="Analyzed sectors")
    
    # Analysis results
    total_decisions: int = Field(0, description="Total decisions analyzed")
    time_period: Dict[str, date] = Field(..., description="Analysis time period (from/to dates)")
    trend_direction: str = Field(..., description="Overall trend (stable/evolving/contradictory)")
    consistency_score: float = Field(0.0, ge=0.0, le=1.0, description="Consistency in decisions")
    
    # Key findings
    dominant_principles: List[str] = Field(default_factory=list, description="Most frequently applied principles")
    recent_changes: List[str] = Field(default_factory=list, description="Recent changes in jurisprudence")
    conflicting_decisions: List[str] = Field(default_factory=list, description="Potentially conflicting decisions")
    
    # Practical implications
    ccnl_implications: List[str] = Field(default_factory=list, description="Implications for CCNL interpretation")
    practice_recommendations: List[str] = Field(default_factory=list, description="Practical recommendations")
    
    # Supporting data
    decision_distribution: Dict[str, int] = Field(default_factory=dict, description="Decision distribution by outcome")
    section_analysis: Dict[str, Any] = Field(default_factory=dict, description="Analysis by court section")
    citation_network: Dict[str, List[str]] = Field(default_factory=dict, description="Citation relationships")


class CassazioneUpdate(PydanticBaseModel):
    """
    Model for tracking Cassazione database updates.
    
    Tracks new decisions, updates to existing decisions,
    and changes in legal principle classifications.
    """
    update_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    update_date: datetime = Field(default_factory=datetime.utcnow)
    update_type: str = Field(..., description="Type of update (new_decision, decision_update, principle_update)")
    
    # Update details
    affected_decisions: List[str] = Field(default_factory=list, description="Decision IDs affected")
    new_decisions: List[str] = Field(default_factory=list, description="Newly added decision IDs")
    updated_principles: List[str] = Field(default_factory=list, description="Updated legal principle IDs")
    
    # Change summary
    total_changes: int = Field(0, description="Total number of changes")
    change_summary: str = Field("", description="Summary of changes made")
    data_source: str = Field("", description="Source of the update data")
    processing_status: str = Field("completed", description="Update processing status")
    
    # Quality metrics
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors encountered")
    confidence_metrics: Dict[str, float] = Field(default_factory=dict, description="Confidence in extracted data")


# Utility functions for legal principle analysis

def extract_legal_keywords(text: str) -> List[str]:
    """Extract legal keywords from decision text."""
    # Common Italian legal terms in labor law
    legal_terms = [
        "contratto collettivo", "ccnl", "licenziamento", "giustificato motivo",
        "giusta causa", "retribuzione", "ferie", "permessi", "malattia",
        "infortunio", "contributi", "previdenza", "sicurezza", "discriminazione",
        "sindacato", "sciopero", "orario di lavoro", "straordinario", "festivo",
        "maternità", "paternità", "congedo", "aspettativa", "preavviso",
        "indennità", "risarcimento", "danno", "mora", "interessi", "rivalutazione"
    ]
    
    text_lower = text.lower() if text else ""
    found_terms = [term for term in legal_terms if term in text_lower]
    return found_terms


def classify_precedent_value(
    section: CassazioneSection,
    decision_type: DecisionType,
    citations_count: int = 0,
    legal_principle_clarity: str = "medium"
) -> str:
    """Classify the precedent value of a Cassazione decision."""
    
    # Base score
    score = 50
    
    # Section importance
    if section == CassazioneSection.SEZIONI_UNITE_CIVILI:
        score += 40
    elif section == CassazioneSection.CIVILE_LAVORO:
        score += 30
    elif section in [CassazioneSection.CIVILE_PRIMA, CassazioneSection.CIVILE_SECONDA]:
        score += 20
    
    # Decision type
    if decision_type == DecisionType.SENTENZA:
        score += 20
    elif decision_type == DecisionType.MASSIMA:
        score += 25
    elif decision_type == DecisionType.ORDINANZA:
        score += 10
    
    # Citations (influence)
    if citations_count > 10:
        score += 15
    elif citations_count > 5:
        score += 10
    elif citations_count > 0:
        score += 5
    
    # Legal principle clarity
    if legal_principle_clarity == "high":
        score += 10
    elif legal_principle_clarity == "low":
        score -= 10
    
    # Classify based on final score
    if score >= 90:
        return "high"
    elif score >= 70:
        return "medium"
    else:
        return "low"


def determine_related_sectors(text: str, legal_areas: List[LegalPrincipleArea]) -> List[CCNLSector]:
    """Determine which CCNL sectors are related to a legal decision."""
    text_lower = text.lower() if text else ""
    related_sectors = []
    
    # Sector-specific keywords mapping
    sector_keywords = {
        CCNLSector.METALMECCANICI_INDUSTRIA: ["metalmeccanici", "industria meccanica", "siderurgia"],
        CCNLSector.EDILIZIA_INDUSTRIA: ["edilizia", "costruzioni", "cantiere", "opere pubbliche"],
        CCNLSector.COMMERCIO_TERZIARIO: ["commercio", "terziario", "vendita", "distribuzione"],
        CCNLSector.SANITA_PRIVATA: ["sanità", "sanitario", "ospedale", "clinica", "medico"],
        CCNLSector.TRASPORTI_LOGISTICA: ["trasporti", "logistica", "autotrasporti", "spedizioni"],
        CCNLSector.TURISMO: ["turismo", "alberghiero", "hotel", "ristorazione"],
        CCNLSector.SCUOLA_PRIVATA: ["scuola", "istruzione", "educativo", "formazione"],
        CCNLSector.CHIMICI_FARMACEUTICI: ["chimico", "farmaceutico", "farmacia"],
        CCNLSector.ALIMENTARI_INDUSTRIA: ["alimentare", "food", "bevande", "industria alimentare"],
        CCNLSector.TESSILI: ["tessile", "abbigliamento", "moda", "confezioni"]
    }
    
    for sector, keywords in sector_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            related_sectors.append(sector)
    
    # If no specific sector keywords found, check legal areas for broad applicability
    if not related_sectors and legal_areas:
        if LegalPrincipleArea.CCNL_INTERPRETAZIONE in legal_areas:
            # CCNL interpretation applies broadly
            related_sectors = [
                CCNLSector.METALMECCANICI_INDUSTRIA,
                CCNLSector.COMMERCIO_TERZIARIO,
                CCNLSector.EDILIZIA_INDUSTRIA
            ]
    
    return related_sectors