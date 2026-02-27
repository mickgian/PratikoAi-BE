"""DEV-377: Enhanced Client Data Rights API — GDPR data rights endpoints.

Implements Article 15 (Access), Article 16 (Rectification),
Article 17 (Erasure), Article 20 (Portability).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database import get_db
from app.services.client_export_service import client_export_service
from app.services.client_gdpr_service import client_gdpr_service
from app.services.client_service import client_service

router = APIRouter(prefix="/data-rights", tags=["data-rights"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RectificationRequest(BaseModel):
    """Request body for GDPR Article 16 — rectification of client data."""

    nome: str | None = None
    email: str | None = None
    phone: str | None = None
    indirizzo: str | None = None
    cap: str | None = None
    comune: str | None = None
    provincia: str | None = None


# ---------------------------------------------------------------------------
# GET /data-rights/access/{client_id} — Article 15 Access
# ---------------------------------------------------------------------------


@router.get("/access/{client_id}")
async def access_client_data(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    x_studio_id: UUID = Header(..., alias="X-Studio-ID"),
    x_user_id: str = Header(..., alias="X-User-ID"),
) -> dict:
    """Restituisce i dati completi del cliente (GDPR Articolo 15 — Diritto di accesso)."""
    client = await client_service.get_by_id(db, client_id=client_id, studio_id=x_studio_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")

    logger.info(
        "gdpr_access_right_exercised",
        client_id=client_id,
        studio_id=str(x_studio_id),
        requested_by=x_user_id,
    )

    return {
        "gdpr_article": "Article 15 — Right of Access",
        "client": {
            "id": client.id,
            "codice_fiscale": client.codice_fiscale,
            "nome": client.nome,
            "tipo_cliente": (
                client.tipo_cliente.value if hasattr(client.tipo_cliente, "value") else str(client.tipo_cliente)
            ),
            "stato_cliente": (
                client.stato_cliente.value if hasattr(client.stato_cliente, "value") else str(client.stato_cliente)
            ),
            "partita_iva": client.partita_iva,
            "email": client.email,
            "phone": client.phone,
            "indirizzo": client.indirizzo,
            "cap": client.cap,
            "comune": client.comune,
            "provincia": client.provincia,
            "note_studio": client.note_studio,
        },
    }


# ---------------------------------------------------------------------------
# GET /data-rights/export/{client_id} — Article 20 Portability
# ---------------------------------------------------------------------------


@router.get("/export/{client_id}")
async def export_client_data(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    x_studio_id: UUID = Header(..., alias="X-Studio-ID"),
    x_user_id: str = Header(..., alias="X-User-ID"),
) -> dict:
    """Esporta i dati del cliente (GDPR Articolo 20 — Diritto alla portabilità)."""
    data = await client_export_service.export_client_by_id(db, studio_id=x_studio_id, client_id=client_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")

    logger.info(
        "gdpr_portability_right_exercised",
        client_id=client_id,
        studio_id=str(x_studio_id),
        requested_by=x_user_id,
    )

    return {
        "gdpr_article": "Article 20 — Right to Data Portability",
        "format": "application/json",
        "data": data,
    }


# ---------------------------------------------------------------------------
# PUT /data-rights/rectify/{client_id} — Article 16 Rectification
# ---------------------------------------------------------------------------


@router.put("/rectify/{client_id}")
async def rectify_client_data(
    client_id: int,
    body: RectificationRequest,
    db: AsyncSession = Depends(get_db),
    x_studio_id: UUID = Header(..., alias="X-Studio-ID"),
    x_user_id: str = Header(..., alias="X-User-ID"),
) -> dict:
    """Rettifica i dati del cliente (GDPR Articolo 16 — Diritto di rettifica)."""
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="Nessun campo da rettificare fornito.")

    client = await client_service.update(db, client_id=client_id, studio_id=x_studio_id, **fields)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")

    await db.commit()

    logger.info(
        "gdpr_rectification_right_exercised",
        client_id=client_id,
        studio_id=str(x_studio_id),
        requested_by=x_user_id,
        rectified_fields=list(fields.keys()),
    )

    return {
        "gdpr_article": "Article 16 — Right to Rectification",
        "rectified_fields": list(fields.keys()),
        "client": {
            "id": client.id,
            "codice_fiscale": client.codice_fiscale,
            "nome": client.nome,
            "tipo_cliente": (
                client.tipo_cliente.value if hasattr(client.tipo_cliente, "value") else str(client.tipo_cliente)
            ),
            "stato_cliente": (
                client.stato_cliente.value if hasattr(client.stato_cliente, "value") else str(client.stato_cliente)
            ),
            "partita_iva": client.partita_iva,
            "email": client.email,
            "phone": client.phone,
            "indirizzo": client.indirizzo,
            "cap": client.cap,
            "comune": client.comune,
            "provincia": client.provincia,
            "note_studio": client.note_studio,
        },
    }


# ---------------------------------------------------------------------------
# DELETE /data-rights/erase/{client_id} — Article 17 Erasure
# ---------------------------------------------------------------------------


@router.delete("/erase/{client_id}")
async def erase_client_data(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    x_studio_id: UUID = Header(..., alias="X-Studio-ID"),
    x_user_id: str = Header(..., alias="X-User-ID"),
) -> dict:
    """Cancella i dati del cliente (GDPR Articolo 17 — Diritto alla cancellazione)."""
    result = await client_gdpr_service.delete_client_gdpr(
        db,
        studio_id=x_studio_id,
        client_id=client_id,
        requested_by=x_user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")

    await db.commit()

    logger.info(
        "gdpr_erasure_right_exercised",
        client_id=client_id,
        studio_id=str(x_studio_id),
        requested_by=x_user_id,
        communications_affected=result.communications_affected,
    )

    return {
        "gdpr_article": "Article 17 — Right to Erasure",
        "client_id": result.client_id,
        "export_data": result.export_data,
        "anonymized_at": result.anonymized_at.isoformat(),
        "communications_affected": result.communications_affected,
    }
