"""DEV-302: ClientProfile SQLModel — 1:1 extension of Client with business metadata.

Contains fiscal/business metadata and a 1536-dimension vector for semantic
matching.  Linked 1:1 to the Client model via client_id FK.
"""

import re
from datetime import date, datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel

# ATECO code regex: XX.XX.XX
_ATECO_RE = re.compile(r"^\d{2}\.\d{2}\.\d{2}$")


class RegimeFiscale(StrEnum):
    """Italian fiscal regime."""

    ORDINARIO = "ordinario"
    SEMPLIFICATO = "semplificato"
    FORFETTARIO = "forfettario"
    AGRICOLO = "agricolo"
    MINIMI = "minimi"


class PosizioneAgenziaEntrate(StrEnum):
    """Status with the Italian tax authority."""

    REGOLARE = "regolare"
    IRREGOLARE = "irregolare"
    IN_VERIFICA = "in_verifica"


class ClientProfile(SQLModel, table=True):  # type: ignore[call-arg]
    """Business/fiscal metadata for a Client (1:1 relationship).

    Attributes:
        id: Auto-increment PK.
        client_id: 1:1 FK → clients.id.
        codice_ateco_principale: Primary ATECO code (XX.XX.XX).
        codici_ateco_secondari: Secondary ATECO codes (ARRAY).
        regime_fiscale: Fiscal regime enum.
        ccnl_applicato: CCNL name (nullable, for employers).
        n_dipendenti: Number of employees (default 0).
        data_inizio_attivita: Business start date.
        data_cessazione_attivita: Business end date (nullable).
        immobili: JSONB array of property objects for IMU/TASI.
        posizione_agenzia_entrate: Tax authority status (nullable).
        profile_vector: 1536-dim vector for semantic matching.
    """

    __tablename__ = "client_profiles"

    # PK
    id: int | None = Field(default=None, primary_key=True)

    # 1:1 FK to Client
    client_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("clients.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
    )

    # ATECO codes
    codice_ateco_principale: str = Field(
        max_length=10,
        description="Primary ATECO code (XX.XX.XX)",
    )
    codici_ateco_secondari: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(10)), nullable=False, server_default="{}"),
        description="Secondary ATECO codes",
    )

    # Fiscal regime
    regime_fiscale: RegimeFiscale = Field(
        sa_column=Column(String(20), nullable=False),
    )

    # Employment
    ccnl_applicato: str | None = Field(
        default=None,
        max_length=100,
        description="CCNL contract name (for employers)",
    )
    n_dipendenti: int = Field(default=0, ge=0)

    # Activity dates
    data_inizio_attivita: date = Field(
        sa_column=Column(Date, nullable=False),
    )
    data_cessazione_attivita: date | None = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )

    # Property data (JSONB)
    immobili: list | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Array of property objects for IMU/TASI calculations",
    )

    # Tax authority status
    posizione_agenzia_entrate: PosizioneAgenziaEntrate | None = Field(
        default=None,
        sa_column=Column(String(15), nullable=True),
    )

    # Semantic matching vector
    profile_vector: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1536), nullable=True),
        description="1536-dim vector for semantic matching",
    )

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    # Indexes
    __table_args__ = (
        Index("ix_client_profiles_regime", "regime_fiscale"),
        Index("ix_client_profiles_ateco", "codice_ateco_principale"),
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_valid_ateco(code: str) -> bool:
        """Validate ATECO code format (XX.XX.XX)."""
        return bool(_ATECO_RE.match(code))

    def __repr__(self) -> str:
        rf = self.regime_fiscale.value if isinstance(self.regime_fiscale, RegimeFiscale) else self.regime_fiscale
        return f"<ClientProfile(client_id={self.client_id}, regime='{rf}')>"
