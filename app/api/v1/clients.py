"""DEV-312: Client API Endpoints — CRUD with pagination and filtering.

Thin route handlers delegating to ClientService.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import StatoCliente
from app.models.database import get_db
from app.schemas.client import ClientCreate, ClientListResponse, ClientResponse, ClientUpdate
from app.services.client_service import client_service

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    body: ClientCreate,
    studio_id: UUID = Query(..., description="ID dello studio"),
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    """Crea un nuovo cliente nello studio."""
    try:
        client = await client_service.create(
            db,
            studio_id=studio_id,
            codice_fiscale=body.codice_fiscale,
            nome=body.nome,
            tipo_cliente=body.tipo_cliente,
            comune=body.comune,
            provincia=body.provincia,
            partita_iva=body.partita_iva,
            email=body.email,
            phone=body.phone,
            indirizzo=body.indirizzo,
            cap=body.cap,
            stato_cliente=body.stato_cliente,
            note_studio=body.note_studio,
        )
        await db.commit()
        return ClientResponse.model_validate(client)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=ClientListResponse)
async def list_clients(
    studio_id: UUID = Query(..., description="ID dello studio"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    stato: StatoCliente | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ClientListResponse:
    """Elenco clienti con paginazione e filtri."""
    clients, total = await client_service.list(db, studio_id=studio_id, offset=offset, limit=limit, stato=stato)
    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in clients],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    studio_id: UUID = Query(..., description="ID dello studio"),
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    """Recupera un cliente per ID."""
    client = await client_service.get_by_id(db, client_id=client_id, studio_id=studio_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    return ClientResponse.model_validate(client)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    body: ClientUpdate,
    studio_id: UUID = Query(..., description="ID dello studio"),
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    """Aggiorna i dati di un cliente."""
    fields = body.model_dump(exclude_unset=True)
    client = await client_service.update(db, client_id=client_id, studio_id=studio_id, **fields)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    await db.commit()
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: int,
    studio_id: UUID = Query(..., description="ID dello studio"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Elimina un cliente (soft-delete GDPR)."""
    client = await client_service.soft_delete(db, client_id=client_id, studio_id=studio_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    await db.commit()
