"""DEV-336: Communication Template SQLModel — Reusable templates.

Templates for communication generation with variable substitution.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel

from app.models.communication import CanaleInvio


class CommunicationTemplate(SQLModel, table=True):  # type: ignore[call-arg]
    """Reusable communication template.

    Attributes:
        id: UUID primary key.
        studio_id: FK → studios.id (tenant isolation).
        name: Template name.
        subject_template: Subject with {{variable}} placeholders.
        content_template: Body with {{variable}} placeholders.
        channel: Default channel for this template.
        category: Template category (e.g. "scadenza", "normativa").
        is_active: Whether the template is available for use.
    """

    __tablename__ = "communication_templates"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    name: str = Field(max_length=200)
    subject_template: str = Field(max_length=300)
    content_template: str = Field(sa_column=Column(Text, nullable=False))

    channel: CanaleInvio = Field(sa_column=Column(String(15), nullable=False))
    category: str = Field(default="generale", max_length=50)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    __table_args__ = (
        Index("ix_comm_templates_studio_active", "studio_id", "is_active"),
        Index("ix_comm_templates_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<CommunicationTemplate(name='{self.name}', channel='{self.channel}')>"
