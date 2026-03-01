"""DEV-431: Formulario SQLModel — Document templates/forms library.

Reference data for standard Italian tax/business forms (e.g., Modello AA9/12, F24, CU).
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class FormularioCategory(StrEnum):
    """Category of formulario."""

    APERTURA = "apertura"
    DICHIARAZIONI = "dichiarazioni"
    VERSAMENTI = "versamenti"
    LAVORO = "lavoro"
    PREVIDENZA = "previdenza"
    ALTRO = "altro"


class Formulario(SQLModel, table=True):  # type: ignore[call-arg]
    """Document template/form from Italian authorities.

    Reference data (pre-seeded), not user-generated.
    """

    __tablename__ = "formulari"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    code: str = Field(
        sa_column=Column(String(30), unique=True, nullable=False, index=True),
    )
    name: str = Field(max_length=200)
    description: str = Field(sa_column=Column(Text, nullable=False))

    category: FormularioCategory = Field(
        sa_column=Column(String(20), nullable=False),
    )

    issuing_authority: str = Field(max_length=100)

    external_url: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    __table_args__ = (Index("ix_formulari_category_active", "category", "is_active"),)

    def __repr__(self) -> str:
        return f"<Formulario(code='{self.code}', name='{self.name}')>"
