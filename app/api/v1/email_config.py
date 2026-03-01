"""DEV-444: Studio Email Config API Endpoints.

REST endpoints for managing per-studio custom SMTP configuration.
Plan gating enforced: Base plan users get 403.
See ADR-034 for design rationale.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.email_config import EmailConfigCreateRequest, EmailConfigResponse
from app.services.studio_email_config_service import studio_email_config_service

router = APIRouter(prefix="/email-config", tags=["email-config"])


@router.post("", response_model=EmailConfigResponse, status_code=201)
async def create_or_update_email_config(
    request: EmailConfigCreateRequest,
    user: User = Depends(get_current_user),
) -> EmailConfigResponse:
    """Create or update SMTP configuration (Pro/Premium only)."""
    try:
        config = await studio_email_config_service.create_or_update_config(
            user=user,
            data=request.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return EmailConfigResponse(
        id=config.id,
        user_id=config.user_id,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_username=config.smtp_username,
        has_password=bool(config.smtp_password_encrypted),
        use_tls=config.use_tls,
        from_email=config.from_email,
        from_name=config.from_name,
        reply_to_email=config.reply_to_email,
        is_verified=config.is_verified,
        is_active=config.is_active,
    )


@router.get("", response_model=EmailConfigResponse)
async def get_email_config(
    user: User = Depends(get_current_user),
) -> EmailConfigResponse:
    """Get SMTP configuration (password field returns has_password instead)."""
    result = await studio_email_config_service.get_config(user)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Nessuna configurazione email trovata",
        )
    return EmailConfigResponse(**result)


@router.delete("")
async def delete_email_config(
    user: User = Depends(get_current_user),
) -> dict:
    """Remove custom SMTP config (reverts to PratikoAI default)."""
    deleted = await studio_email_config_service.delete_config(user)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Nessuna configurazione email da eliminare",
        )
    return {"success": True, "message": "Configurazione email rimossa. Verrà usato il servizio PratikoAI predefinito."}


@router.post("/test")
async def test_email_config(
    user: User = Depends(get_current_user),
) -> dict:
    """Test SMTP config by verifying connection (rate limited: 5/hour)."""
    success = await studio_email_config_service.verify_config(user)
    if not success:
        raise HTTPException(
            status_code=422,
            detail="Verifica SMTP fallita. Controlla le credenziali e le impostazioni del server.",
        )
    return {
        "success": True,
        "verified": True,
        "message": "Configurazione SMTP verificata con successo.",
    }
