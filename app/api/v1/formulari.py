"""DEV-432: Formulari API Endpoint — Thin handlers for formulari library."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.formulario_service import formulario_service

router = APIRouter(prefix="/formulari", tags=["formulari"])


class FormularioResponse(BaseModel):
    """Response schema for a formulario."""

    id: UUID
    code: str
    name: str
    description: str
    category: str
    issuing_authority: str
    external_url: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class FormularioCountResponse(BaseModel):
    """Response schema for formulari count."""

    count: int


@router.get("", response_model=list[FormularioResponse])
async def list_formulari(
    category: str | None = Query(default=None, description="Filtra per categoria"),
    search: str | None = Query(default=None, description="Ricerca testuale"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[FormularioResponse]:
    """Elenco modelli e formulari."""
    from app.models.formulario import FormularioCategory

    cat = None
    if category:
        try:
            cat = FormularioCategory(category.lower())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Categoria non valida: {category}")

    items = await formulario_service.list_formulari(
        db,
        category=cat,
        search=search,
        offset=offset,
        limit=limit,
    )
    return [FormularioResponse.model_validate(f) for f in items]


@router.get("/count", response_model=FormularioCountResponse)
async def count_formulari(
    category: str | None = Query(default=None, description="Filtra per categoria"),
    db: AsyncSession = Depends(get_db),
) -> FormularioCountResponse:
    """Conteggio formulari attivi."""
    from app.models.formulario import FormularioCategory

    cat = None
    if category:
        try:
            cat = FormularioCategory(category.lower())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Categoria non valida: {category}")

    count = await formulario_service.count_formulari(db, category=cat)
    return FormularioCountResponse(count=count)


@router.get("/{formulario_id}", response_model=FormularioResponse)
async def get_formulario(
    formulario_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FormularioResponse:
    """Dettaglio di un singolo formulario."""
    item = await formulario_service.get_formulario(db, formulario_id=formulario_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Formulario non trovato.")
    return FormularioResponse.model_validate(item)
