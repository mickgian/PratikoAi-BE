"""DEV-316: Tenant Context Middleware -- Extracts studio_id from JWT.

Sets studio_id in request.state for downstream services to access
via the get_current_studio_id dependency.
"""

from uuid import UUID

from fastapi import HTTPException, Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import logger

# Paths that bypass tenant context authentication
_BYPASS_PATHS: set[str] = {
    "/health",
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/openapi.json",
    "/metrics",
}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts studio_id from JWT and sets it in request state.

    Skips authentication for:
    - OPTIONS requests (CORS preflight)
    - Health check endpoints (/health, /api/v1/health)
    - OpenAPI documentation endpoints (/docs, /redoc, /openapi.json)
    """

    async def dispatch(self, request: StarletteRequest, call_next) -> Response:
        """Process the request, extract JWT, and set studio_id in state."""
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip bypass paths (health checks, docs)
        if request.url.path in _BYPASS_PATHS:
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            logger.warning(
                "tenant_context_missing_auth",
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Token di autenticazione mancante."},
            )

        # Validate Bearer scheme
        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0] != "Bearer":
            logger.warning(
                "tenant_context_invalid_auth_scheme",
                path=request.url.path,
                scheme=parts[0] if parts else "empty",
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Schema di autenticazione non valido. Usa 'Bearer <token>'."},
            )

        token = parts[1]

        # Decode JWT
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError as e:
            logger.warning(
                "tenant_context_jwt_decode_failed",
                path=request.url.path,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Token non valido o scaduto."},
            )

        # Extract studio_id from claims
        studio_id_raw = payload.get("studio_id")
        if not studio_id_raw:
            logger.warning(
                "tenant_context_missing_studio_id",
                path=request.url.path,
                sub=payload.get("sub"),
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Studio non associato all'utente."},
            )

        # Parse studio_id as UUID
        try:
            studio_id = UUID(str(studio_id_raw))
        except (ValueError, AttributeError):
            logger.warning(
                "tenant_context_invalid_studio_id",
                path=request.url.path,
                studio_id_raw=str(studio_id_raw),
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Studio non associato all'utente."},
            )

        # Set studio_id in request state for downstream access
        request.state.studio_id = studio_id

        logger.debug(
            "tenant_context_set",
            studio_id=str(studio_id),
            path=request.url.path,
            method=request.method,
        )

        return await call_next(request)


def get_current_studio_id(request: Request) -> UUID:
    """Dependency to get studio_id from request state (set by middleware).

    Use with FastAPI's Depends():
        @router.get("/endpoint")
        async def endpoint(studio_id: UUID = Depends(get_current_studio_id)):
            ...

    Returns:
        UUID: The studio_id extracted from the JWT by the middleware.

    Raises:
        HTTPException: 403 if studio_id is not set in request state.
    """
    studio_id = getattr(request.state, "studio_id", None)
    if studio_id is None:
        raise HTTPException(status_code=403, detail="Studio non associato all'utente.")
    return studio_id
