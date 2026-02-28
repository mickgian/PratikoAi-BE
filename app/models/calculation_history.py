"""DEV-352: CalculationHistory SQLModel — Stores calculations for audit.

Records all fiscal calculations performed for clients, enabling
audit trail and historical reference.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class CalculationHistory(SQLModel, table=True):  # type: ignore[call-arg]
    """Calculation history for client records and audit.

    Attributes:
        id: UUID primary key.
        studio_id: FK → studios.id (multi-tenant).
        client_id: FK → clients.id (nullable for anonymous calcs).
        calculation_type: Type of calculation performed.
        input_data: JSONB input parameters.
        result_data: JSONB calculation results.
        performed_by: FK → user.id who triggered the calculation.
    """

    __tablename__ = "calculation_history"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    client_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True, index=True),
    )

    calculation_type: str = Field(
        sa_column=Column(String(50), nullable=False, index=True),
    )

    input_data: dict | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    result_data: dict | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    notes: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    performed_by: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    __table_args__ = (
        Index("ix_calc_history_studio_type", "studio_id", "calculation_type"),
        Index("ix_calc_history_client", "client_id", "calculation_type"),
    )

    def __repr__(self) -> str:
        return f"<CalculationHistory(type='{self.calculation_type}', client_id={self.client_id})>"
