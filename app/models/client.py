"""DEV-301: Client SQLModel — Studio client with encrypted PII.

Each client belongs to a Studio (multi-tenant FK) and stores personally
identifiable information encrypted at rest via EncryptedType decorators.
Soft delete is supported for GDPR right-to-erasure compliance.
"""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Column, Date, DateTime, Index, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel

from app.core.encryption.encrypted_types import (
    EncryptedEmail,
    EncryptedPersonalData,
    EncryptedPhone,
    EncryptedTaxID,
)


class TipoCliente(StrEnum):
    """Client legal-entity type."""

    PERSONA_FISICA = "persona_fisica"
    DITTA_INDIVIDUALE = "ditta_individuale"
    SOCIETA = "societa"
    ENTE = "ente"


class StatoCliente(StrEnum):
    """Client lifecycle state."""

    ATTIVO = "attivo"
    PROSPECT = "prospect"
    CESSATO = "cessato"
    SOSPESO = "sospeso"


class Client(SQLModel, table=True):  # type: ignore[call-arg]
    """Studio client with encrypted PII fields.

    Attributes:
        id: Auto-increment PK.
        studio_id: FK → studios.id (multi-tenant isolation).
        codice_fiscale: Italian tax code (encrypted).
        partita_iva: VAT number (encrypted, nullable).
        nome: Full name (encrypted).
        tipo_cliente: Legal-entity type enum.
        email / phone: Contact info (encrypted, nullable).
        indirizzo / cap / comune / provincia: Address fields.
        stato_cliente: Lifecycle state (default ATTIVO).
        data_nascita_titolare: Owner's date of birth (nullable).
        note_studio: Internal studio notes (nullable).
        created_at / updated_at: Audit timestamps.
        deleted_at: Soft-delete marker (GDPR).
    """

    __tablename__ = "clients"

    # PK
    id: int | None = Field(default=None, primary_key=True)

    # Multi-tenant FK
    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    # Encrypted PII fields
    codice_fiscale: str = Field(
        sa_column=Column(EncryptedTaxID(50), nullable=False),
        description="Italian tax ID — Codice Fiscale (encrypted)",
    )
    partita_iva: str | None = Field(
        default=None,
        sa_column=Column(EncryptedTaxID(50), nullable=True),
        description="VAT number — Partita IVA (encrypted)",
    )
    nome: str = Field(
        sa_column=Column(EncryptedPersonalData(200), nullable=False),
        description="Full name (encrypted)",
    )
    email: str | None = Field(
        default=None,
        sa_column=Column(EncryptedEmail(255), nullable=True),
        description="Email address (encrypted)",
    )
    phone: str | None = Field(
        default=None,
        sa_column=Column(EncryptedPhone(50), nullable=True),
        description="Phone number (encrypted)",
    )

    # Enum fields
    tipo_cliente: TipoCliente = Field(
        sa_column=Column(String(30), nullable=False),
    )
    stato_cliente: StatoCliente = Field(
        default=StatoCliente.ATTIVO,
        sa_column=Column(String(20), nullable=False, server_default="attivo"),
    )

    # Address (plain-text — not considered sensitive PII per DPIA)
    indirizzo: str | None = Field(default=None, max_length=300)
    cap: str | None = Field(default=None, max_length=5)
    comune: str = Field(max_length=100)
    provincia: str = Field(max_length=2)

    # Extra fields
    data_nascita_titolare: date | None = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )
    note_studio: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Indexes
    __table_args__ = (Index("ix_clients_studio_stato", "studio_id", "stato_cliente"),)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_deleted(self) -> bool:
        """Return True when soft-deleted."""
        return self.deleted_at is not None

    def __repr__(self) -> str:
        tc = self.tipo_cliente.value if isinstance(self.tipo_cliente, TipoCliente) else self.tipo_cliente
        return f"<Client(nome='{self.nome}', tipo='{tc}')>"
