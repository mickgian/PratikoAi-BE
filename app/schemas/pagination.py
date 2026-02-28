"""DEV-368: Standardized pagination schema.

Provides consistent pagination format across all list endpoints.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    page: int = Field(default=1, ge=1, description="Numero pagina (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Elementi per pagina")

    @property
    def offset(self) -> int:
        """Calculate SQL offset from page number."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):  # noqa: UP046
    """Standard paginated response wrapper.

    All list endpoints should return this format.
    """

    items: list[T] = Field(description="Elementi della pagina corrente")
    total: int = Field(ge=0, description="Totale elementi disponibili")
    page: int = Field(ge=1, description="Pagina corrente")
    page_size: int = Field(ge=1, description="Elementi per pagina")
    total_pages: int = Field(ge=0, description="Numero totale pagine")

    model_config = {"from_attributes": True}
