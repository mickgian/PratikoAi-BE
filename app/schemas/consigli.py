"""Schemas for /consigli insight report (ADR-038)."""

from pydantic import BaseModel


class ConsigliReportResponse(BaseModel):
    """Response for /consigli report generation."""

    status: str  # "success" | "insufficient_data" | "generating" | "error"
    message_it: str
    html_report: str | None = None
    stats_summary: dict | None = None


class ConsigliSufficiencyResponse(BaseModel):
    """Response for /consigli data sufficiency check."""

    can_generate: bool
    message_it: str
    query_count: int
    history_days: int
