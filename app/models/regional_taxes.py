"""
Regional Tax Models for Italian Tax Variations.

This module defines database models for handling Italian regional and municipal
tax variations including IMU, IRAP, and IRPEF addizionali.

Models:
- Regione: Italian regions with tax autonomy information
- Comune: Italian municipalities with geographic data
- RegionalTaxRate: Regional tax rates (IRAP, addizionale regionale IRPEF)  
- ComunalTaxRate: Municipal tax rates (IMU, addizionale comunale IRPEF)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import uuid4, UUID

from sqlalchemy import (
    Column, String, Numeric, Date, Boolean, ForeignKey, 
    Integer, DateTime, Text, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.ccnl_database import Base


class Regione(Base):
    """
    Italian regions with tax autonomy information.
    
    Represents the 20 Italian regions including special autonomous regions
    like Trentino-Alto Adige, Valle d'Aosta, and the autonomous provinces.
    """
    __tablename__ = "regioni"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    codice_istat = Column(String(2), unique=True, nullable=False, index=True)
    nome = Column(String(50), nullable=False, unique=True)
    
    # Special status information
    is_autonomous = Column(Boolean, default=False, nullable=False)
    has_special_statute = Column(Boolean, default=False, nullable=False)
    
    # Geographic information
    area_kmq = Column(Integer)  # Area in square kilometers
    popolazione = Column(Integer)  # Population
    
    # Administrative details
    capoluogo = Column(String(50))  # Regional capital
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    comuni = relationship("Comune", back_populates="regione", cascade="all, delete-orphan")
    tax_rates = relationship("RegionalTaxRate", back_populates="regione", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Regione(nome='{self.nome}', codice_istat='{self.codice_istat}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "codice_istat": self.codice_istat,
            "nome": self.nome,
            "is_autonomous": self.is_autonomous,
            "has_special_statute": self.has_special_statute,
            "area_kmq": self.area_kmq,
            "popolazione": self.popolazione,
            "capoluogo": self.capoluogo
        }


class Comune(Base):
    """
    Italian municipalities (comuni) with geographic and administrative data.
    
    Contains detailed information about Italian municipalities including
    postal codes, population, and administrative classification.
    """
    __tablename__ = "comuni"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    codice_istat = Column(String(6), unique=True, nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    
    # Geographic hierarchy
    provincia = Column(String(2), nullable=False, index=True)  # RM, MI, NA, etc.
    regione_id = Column(PG_UUID(as_uuid=True), ForeignKey("regioni.id"), nullable=False)
    
    # Postal codes (multiple CAPs per comune)
    cap_codes = Column(ARRAY(String(5)), nullable=False, index=True)
    
    # Administrative classification
    is_capoluogo = Column(Boolean, default=False, nullable=False)
    is_capoluogo_provincia = Column(Boolean, default=False, nullable=False)
    is_metropolitan_city = Column(Boolean, default=False, nullable=False)
    
    # Population and area
    popolazione = Column(Integer)
    area_kmq = Column(Numeric(8, 2))  # Area in square kilometers
    densita_abitativa = Column(Numeric(8, 2))  # Inhabitants per km²
    
    # Geographic coordinates
    latitudine = Column(Numeric(10, 7))
    longitudine = Column(Numeric(10, 7))
    altitudine = Column(Integer)  # Meters above sea level
    
    # Administrative details
    sindaco = Column(String(100))  # Current mayor
    telefono = Column(String(20))
    email = Column(String(100))
    pec = Column(String(100))  # Certified email
    sito_web = Column(String(200))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    regione = relationship("Regione", back_populates="comuni")
    tax_rates = relationship("ComunalTaxRate", back_populates="comune", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_comuni_provincia_nome', 'provincia', 'nome'),
        Index('idx_comuni_cap_search', 'cap_codes'),
        Index('idx_comuni_popolazione', 'popolazione'),
    )
    
    def __repr__(self):
        return f"<Comune(nome='{self.nome}', provincia='{self.provincia}')>"
    
    def get_primary_cap(self) -> Optional[str]:
        """Get the primary postal code for this comune"""
        return self.cap_codes[0] if self.cap_codes else None
    
    def has_cap(self, cap: str) -> bool:
        """Check if this comune includes the given CAP"""
        return cap in (self.cap_codes or [])
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "codice_istat": self.codice_istat,
            "nome": self.nome,
            "provincia": self.provincia,
            "regione_id": str(self.regione_id),
            "cap_codes": self.cap_codes,
            "is_capoluogo": self.is_capoluogo,
            "is_capoluogo_provincia": self.is_capoluogo_provincia,
            "is_metropolitan_city": self.is_metropolitan_city,
            "popolazione": self.popolazione,
            "area_kmq": float(self.area_kmq) if self.area_kmq else None,
            "densita_abitativa": float(self.densita_abitativa) if self.densita_abitativa else None,
            "primary_cap": self.get_primary_cap()
        }


class RegionalTaxRate(Base):
    """
    Regional tax rates for IRAP and addizionale regionale IRPEF.
    
    Stores tax rates that vary by region, including different rates
    for different business categories (standard, banks, insurance, agriculture).
    """
    __tablename__ = "regional_tax_rates"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    regione_id = Column(PG_UUID(as_uuid=True), ForeignKey("regioni.id"), nullable=False)
    tax_type = Column(String(50), nullable=False, index=True)  # IRAP, ADDIZIONALE_IRPEF
    
    # Different rates by business category (for IRAP)
    rate_standard = Column(Numeric(5, 2), nullable=False)  # Standard business rate
    rate_banks = Column(Numeric(5, 2))  # Banks and financial institutions
    rate_insurance = Column(Numeric(5, 2))  # Insurance companies
    rate_agriculture = Column(Numeric(5, 2))  # Agricultural activities
    rate_cooperatives = Column(Numeric(5, 2))  # Cooperative societies
    
    # Validity period
    valid_from = Column(Date, nullable=False, index=True)
    valid_to = Column(Date, index=True)  # NULL means currently valid
    
    # Additional parameters
    minimum_tax = Column(Numeric(10, 2))  # Minimum tax amount
    maximum_tax = Column(Numeric(12, 2))  # Maximum tax amount
    exemption_threshold = Column(Numeric(12, 2))  # Revenue threshold for exemption
    
    # Calculation parameters stored as JSON
    calculation_parameters = Column(JSONB)  # Flexible parameters
    
    # Legislative reference
    legislative_reference = Column(Text)  # Law or decree reference
    notes = Column(Text)  # Additional notes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    regione = relationship("Regione", back_populates="tax_rates")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('regione_id', 'tax_type', 'valid_from', 
                        name='uq_regional_tax_rate_period'),
        Index('idx_regional_tax_rates_lookup', 'regione_id', 'tax_type', 'valid_from', 'valid_to'),
    )
    
    def __repr__(self):
        return f"<RegionalTaxRate(regione_id='{self.regione_id}', tax_type='{self.tax_type}', rate={self.rate_standard})>"
    
    def get_rate_for_business_type(self, business_type: str) -> Decimal:
        """Get the appropriate rate for a specific business type"""
        rate_mapping = {
            "standard": self.rate_standard,
            "banks": self.rate_banks or self.rate_standard,
            "insurance": self.rate_insurance or self.rate_standard,
            "agriculture": self.rate_agriculture or self.rate_standard,
            "cooperatives": self.rate_cooperatives or self.rate_standard
        }
        return rate_mapping.get(business_type, self.rate_standard)
    
    def is_valid_on_date(self, reference_date: date) -> bool:
        """Check if this rate is valid on the given date"""
        if reference_date < self.valid_from:
            return False
        if self.valid_to and reference_date > self.valid_to:
            return False
        return True
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "regione_id": str(self.regione_id),
            "tax_type": self.tax_type,
            "rate_standard": float(self.rate_standard),
            "rate_banks": float(self.rate_banks) if self.rate_banks else None,
            "rate_insurance": float(self.rate_insurance) if self.rate_insurance else None,
            "rate_agriculture": float(self.rate_agriculture) if self.rate_agriculture else None,
            "rate_cooperatives": float(self.rate_cooperatives) if self.rate_cooperatives else None,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "minimum_tax": float(self.minimum_tax) if self.minimum_tax else None,
            "maximum_tax": float(self.maximum_tax) if self.maximum_tax else None,
            "exemption_threshold": float(self.exemption_threshold) if self.exemption_threshold else None,
            "calculation_parameters": self.calculation_parameters,
            "legislative_reference": self.legislative_reference,
            "notes": self.notes
        }


class ComunalTaxRate(Base):
    """
    Municipal tax rates for IMU and addizionale comunale IRPEF.
    
    Stores tax rates that vary by municipality, including special rates
    for different property types and income thresholds.
    """
    __tablename__ = "comunal_tax_rates"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    comune_id = Column(PG_UUID(as_uuid=True), ForeignKey("comuni.id"), nullable=False)
    tax_type = Column(String(50), nullable=False, index=True)  # IMU, ADDIZIONALE_COMUNALE_IRPEF
    
    # Basic rate information
    rate = Column(Numeric(5, 2), nullable=False)  # Standard rate percentage
    rate_prima_casa = Column(Numeric(5, 2))  # Rate for primary residence (IMU)
    rate_altri_immobili = Column(Numeric(5, 2))  # Rate for other properties (IMU)
    rate_commerciale = Column(Numeric(5, 2))  # Rate for commercial properties
    rate_industriale = Column(Numeric(5, 2))  # Rate for industrial properties
    rate_agricolo = Column(Numeric(5, 2))  # Rate for agricultural properties
    
    # Exemptions and special provisions
    esenzione_prima_casa = Column(Boolean, default=False, nullable=False)
    esenzione_giovani_coppie = Column(Boolean, default=False)  # Young couples exemption
    esenzione_over_65 = Column(Boolean, default=False)  # Elderly exemption
    
    # Validity period
    valid_from = Column(Date, nullable=False, index=True)
    valid_to = Column(Date, index=True)  # NULL means currently valid
    
    # Deductions and thresholds
    detrazioni = Column(JSONB)  # Deductions by category
    soglie = Column(JSONB)  # Income/value thresholds
    
    # Examples of detrazioni structure:
    # {
    #   "abitazione_principale": 200,
    #   "figli_a_carico": 50,
    #   "anziani_over_75": 100
    # }
    
    # Examples of soglie structure:
    # {
    #   "no_tax_under": 11000,  # No tax under this income
    #   "reduced_rate_under": 15000,  # Reduced rate under this income
    #   "property_value_exemption": 500000  # Property value exemption limit
    # }
    
    # Additional municipal provisions
    maggiorazioni = Column(JSONB)  # Rate increases for specific categories
    agevolazioni = Column(JSONB)  # Municipal incentives and reductions
    
    # Legislative reference
    delibera_comunale = Column(String(50))  # Municipal resolution number
    data_delibera = Column(Date)  # Resolution date
    legislative_reference = Column(Text)  # Full legislative reference
    notes = Column(Text)  # Additional notes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    comune = relationship("Comune", back_populates="tax_rates")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('comune_id', 'tax_type', 'valid_from', 
                        name='uq_comunal_tax_rate_period'),
        Index('idx_comunal_tax_rates_lookup', 'comune_id', 'tax_type', 'valid_from', 'valid_to'),
    )
    
    def __repr__(self):
        return f"<ComunalTaxRate(comune_id='{self.comune_id}', tax_type='{self.tax_type}', rate={self.rate})>"
    
    def get_rate_for_property_type(self, property_type: str, is_prima_casa: bool = False) -> Decimal:
        """Get the appropriate rate for a specific property type"""
        if self.tax_type == "IMU":
            if is_prima_casa and self.esenzione_prima_casa:
                return Decimal("0")
            elif is_prima_casa and self.rate_prima_casa:
                return self.rate_prima_casa
            
            property_rate_mapping = {
                "standard": self.rate,
                "commerciale": self.rate_commerciale or self.rate,
                "industriale": self.rate_industriale or self.rate,
                "agricolo": self.rate_agricolo or self.rate
            }
            return property_rate_mapping.get(property_type, self.rate)
        
        return self.rate
    
    def get_detrazioni_for_category(self, category: str) -> Decimal:
        """Get deductions for a specific category"""
        if not self.detrazioni:
            return Decimal("0")
        return Decimal(str(self.detrazioni.get(category, 0)))
    
    def has_income_threshold_exemption(self, income: Decimal) -> bool:
        """Check if income is below exemption threshold"""
        if not self.soglie:
            return False
        threshold = self.soglie.get("no_tax_under")
        if threshold and income < Decimal(str(threshold)):
            return True
        return False
    
    def get_reduced_rate_if_applicable(self, income: Decimal) -> Optional[Decimal]:
        """Get reduced rate if income qualifies"""
        if not self.soglie:
            return None
        threshold = self.soglie.get("reduced_rate_under")
        if threshold and income < Decimal(str(threshold)):
            return self.rate * Decimal("0.5")  # 50% reduction example
        return None
    
    def is_valid_on_date(self, reference_date: date) -> bool:
        """Check if this rate is valid on the given date"""
        if reference_date < self.valid_from:
            return False
        if self.valid_to and reference_date > self.valid_to:
            return False
        return True
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "comune_id": str(self.comune_id),
            "tax_type": self.tax_type,
            "rate": float(self.rate),
            "rate_prima_casa": float(self.rate_prima_casa) if self.rate_prima_casa else None,
            "rate_altri_immobili": float(self.rate_altri_immobili) if self.rate_altri_immobili else None,
            "rate_commerciale": float(self.rate_commerciale) if self.rate_commerciale else None,
            "rate_industriale": float(self.rate_industriale) if self.rate_industriale else None,
            "rate_agricolo": float(self.rate_agricolo) if self.rate_agricolo else None,
            "esenzione_prima_casa": self.esenzione_prima_casa,
            "esenzione_giovani_coppie": self.esenzione_giovani_coppie,
            "esenzione_over_65": self.esenzione_over_65,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "detrazioni": self.detrazioni,
            "soglie": self.soglie,
            "maggiorazioni": self.maggiorazioni,
            "agevolazioni": self.agevolazioni,
            "delibera_comunale": self.delibera_comunale,
            "data_delibera": self.data_delibera.isoformat() if self.data_delibera else None,
            "legislative_reference": self.legislative_reference,
            "notes": self.notes
        }


# Pre-populated default data for major Italian locations
DEFAULT_REGIONAL_DATA = {
    "regioni": [
        {
            "codice_istat": "12", "nome": "Lazio", "capoluogo": "Roma",
            "is_autonomous": False, "has_special_statute": False
        },
        {
            "codice_istat": "03", "nome": "Lombardia", "capoluogo": "Milano", 
            "is_autonomous": False, "has_special_statute": False
        },
        {
            "codice_istat": "15", "nome": "Campania", "capoluogo": "Napoli",
            "is_autonomous": False, "has_special_statute": False
        },
        {
            "codice_istat": "01", "nome": "Piemonte", "capoluogo": "Torino",
            "is_autonomous": False, "has_special_statute": False
        },
        {
            "codice_istat": "19", "nome": "Sicilia", "capoluogo": "Palermo",
            "is_autonomous": True, "has_special_statute": True
        },
        {
            "codice_istat": "04", "nome": "Trentino-Alto Adige", "capoluogo": "Trento",
            "is_autonomous": True, "has_special_statute": True
        }
    ],
    "major_comuni": [
        {
            "codice_istat": "058091", "nome": "Roma", "provincia": "RM",
            "cap_codes": ["00100", "00118", "00119", "00120", "00121", "00122", "00123", "00124"],
            "popolazione": 2872800, "is_capoluogo": True, "is_capoluogo_provincia": True
        },
        {
            "codice_istat": "015146", "nome": "Milano", "provincia": "MI",
            "cap_codes": ["20100", "20121", "20122", "20123", "20124", "20125", "20126", "20127"],
            "popolazione": 1396059, "is_capoluogo": True, "is_capoluogo_provincia": True
        },
        {
            "codice_istat": "063049", "nome": "Napoli", "provincia": "NA",
            "cap_codes": ["80100", "80121", "80122", "80123", "80124", "80125", "80126", "80127"],
            "popolazione": 967069, "is_capoluogo": True, "is_capoluogo_provincia": True
        },
        {
            "codice_istat": "001272", "nome": "Torino", "provincia": "TO",
            "cap_codes": ["10100", "10121", "10122", "10123", "10124", "10125", "10126", "10127"],
            "popolazione": 870952, "is_capoluogo": True, "is_capoluogo_provincia": True
        }
    ]
}

# Default tax rates for major cities (2024 values)
DEFAULT_TAX_RATES = {
    "IMU": {
        "Roma": {
            "rate": 1.06, "rate_prima_casa": 0.5, "esenzione_prima_casa": True,
            "detrazioni": {"abitazione_principale": 200}
        },
        "Milano": {
            "rate": 1.04, "rate_prima_casa": 0.6, "esenzione_prima_casa": False,
            "detrazioni": {"abitazione_principale": 300}
        },
        "Napoli": {
            "rate": 1.14, "rate_prima_casa": 0.6, "esenzione_prima_casa": False,
            "detrazioni": {"abitazione_principale": 200}
        },
        "Torino": {
            "rate": 1.06, "rate_prima_casa": 0.45, "esenzione_prima_casa": True,
            "detrazioni": {"abitazione_principale": 200}
        }
    },
    "IRAP": {
        "Lazio": {"rate_standard": 4.82, "rate_banks": 5.57, "rate_insurance": 6.82, "rate_agriculture": 1.9},
        "Lombardia": {"rate_standard": 3.9, "rate_banks": 5.57, "rate_insurance": 6.82, "rate_agriculture": 1.9},
        "Campania": {"rate_standard": 3.9, "rate_banks": 5.57, "rate_insurance": 6.82, "rate_agriculture": 1.9},
        "Piemonte": {"rate_standard": 3.9, "rate_banks": 5.57, "rate_insurance": 6.82, "rate_agriculture": 1.9}
    },
    "ADDIZIONALE_REGIONALE": {
        "Lazio": 1.73, "Lombardia": 1.73, "Campania": 2.03, "Piemonte": 1.68, "Sicilia": 1.4
    },
    "ADDIZIONALE_COMUNALE": {
        "Roma": {"rate": 0.9, "soglie": {"no_tax_under": 11000}},
        "Milano": {"rate": 0.8, "soglie": {"no_tax_under": 15000}},
        "Napoli": {"rate": 0.8, "soglie": {"no_tax_under": 12000}},
        "Torino": {"rate": 0.8, "soglie": {"no_tax_under": 14000}}
    }
}