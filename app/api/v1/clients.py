"""DEV-312: Client API Endpoints — CRUD with pagination, filtering, import and preview.

Thin route handlers delegating to ClientService, ClientImportService,
and ProfileCompletenessService.
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import StatoCliente
from app.models.database import get_db
from app.schemas.client import (
    ClientCreate,
    ClientImportResponse,
    ClientImportWarningsSummary,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    ImportPreviewResponse,
    ImportPreviewRow,
    SuggestedColumnMappingSchema,
)
from app.services.client_import_service import client_import_service
from app.services.client_service import client_service
from app.services.profile_completeness_service import profile_completeness_service

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


@router.post("/import/preview", response_model=ImportPreviewResponse)
async def preview_import(
    studio_id: UUID = Query(..., description="ID dello studio"),
    file: UploadFile = File(...),
) -> ImportPreviewResponse:
    """Parse and validate an import file without writing to DB."""
    content = await file.read()
    filename = (file.filename or "").lower()

    try:
        if filename.endswith((".xlsx", ".xls")):
            headers, records = client_import_service.parse_excel(content)
        elif filename.endswith(".csv"):
            headers, records = client_import_service.parse_csv(content)
        elif filename.endswith(".pdf"):
            headers, records = client_import_service.parse_pdf(content)
        else:
            raise HTTPException(
                status_code=400,
                detail="Formato file non supportato. Usa Excel (.xlsx), CSV (.csv) o PDF (.pdf).",
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    preview_rows = client_import_service.validate_records(records)
    valid_count = sum(1 for r in preview_rows if r.is_valid)

    # Auto-detect column mappings (Tier 1: aliases, Tier 2: fuzzy, Tier 3: data patterns)
    sample_rows = records[:10] if records else []
    suggested = client_import_service.auto_detect_column_mapping(headers, sample_rows)
    suggested_schemas = {
        field: SuggestedColumnMappingSchema(
            file_column=m.file_column,
            confidence=m.confidence,
            match_method=m.match_method,
        )
        for field, m in suggested.items()
    }

    return ImportPreviewResponse(
        detected_columns=headers,
        suggested_mappings=suggested_schemas,
        total_rows=len(preview_rows),
        valid_rows=valid_count,
        invalid_rows=len(preview_rows) - valid_count,
        rows=[
            ImportPreviewRow(
                row_number=r.row_number,
                data=r.data,
                is_valid=r.is_valid,
                errors=r.errors,
            )
            for r in preview_rows
        ],
    )


@router.post("/import", response_model=ClientImportResponse)
async def import_clients(
    studio_id: UUID = Query(..., description="ID dello studio"),
    file: UploadFile = File(...),
    column_mapping: str | None = Form(default=None),
    x_user_id: int | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> ClientImportResponse:
    """Importa clienti da file Excel, CSV o PDF."""
    content = await file.read()
    filename = (file.filename or "").lower()

    mapping: dict[str, str] | None = None
    if column_mapping:
        try:
            mapping = json.loads(column_mapping)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="column_mapping non è un JSON valido.")

    try:
        if filename.endswith((".xlsx", ".xls")):
            report = await client_import_service.import_from_excel(
                db,
                studio_id=studio_id,
                file_content=content,
                column_mapping=mapping,
            )
        elif filename.endswith(".csv"):
            report = await client_import_service.import_from_csv(
                db,
                studio_id=studio_id,
                file_content=content,
                column_mapping=mapping,
            )
        elif filename.endswith(".pdf"):
            report = await client_import_service.import_from_pdf(
                db,
                studio_id=studio_id,
                file_content=content,
                column_mapping=mapping,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Formato file non supportato. Usa Excel (.xlsx), CSV (.csv) o PDF (.pdf).",
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await db.commit()

    # Post-import: analyze completeness and optionally fire notification
    warnings = None
    if report.created_client_ids:
        completeness = await profile_completeness_service.analyze_imported_clients(
            db,
            client_ids=report.created_client_ids,
            studio_id=studio_id,
        )
        warnings = ClientImportWarningsSummary(
            clients_without_profile=completeness.clients_without_profile,
            clients_missing_partita_iva=completeness.clients_missing_partita_iva,
            missing_fields=[
                {
                    "client_id": w.client_id,
                    "client_nome": w.client_nome,
                    "field": w.field,
                    "priority": w.priority,
                    "reason": w.reason,
                }
                for w in completeness.missing_fields
            ],
        )

        if x_user_id and completeness.clients_without_profile > 0:
            from app.services.notification_trigger_service import notification_trigger_service

            await notification_trigger_service.trigger_profilo_incompleto(
                db,
                user_id=x_user_id,
                studio_id=studio_id,
                clients_count=completeness.clients_without_profile,
                description=(
                    f"{completeness.clients_without_profile} clienti importati "
                    "non hanno un profilo aziendale. Completa i dati per "
                    "abilitare il matching normativo."
                ),
            )
            await db.commit()

    return ClientImportResponse(
        total=report.total,
        success_count=report.success_count,
        error_count=report.error_count,
        errors=[{"row_number": e.row_number, "field": e.field, "message": e.message} for e in report.errors],
        warnings=warnings,
    )


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
