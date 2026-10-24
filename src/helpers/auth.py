import secrets

from fastapi import FastAPI, APIRouter, Depends, status, Header, HTTPException, Request
from helpers.config import get_settings


async def require_service_api_key(request: Request) -> None:
    """Require the service token on data and nlp routes when one is configured.

    An empty ``MINIRAG_SERVICE_API_KEY`` leaves those routes open so local
    development keeps working. A configured key accepts either
    ``Authorization: Bearer <token>`` or ``X-Service-Key``.
    """
    expected = (get_settings().MINIRAG_SERVICE_API_KEY or "").strip()
    if not expected:
        return

    provided = ""
    authorization = request.headers.get("authorization") or ""
    if authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    if not provided:
        provided = (request.headers.get("x-service-key") or "").strip()

    provided_bytes = provided.encode("utf-8")
    expected_bytes = expected.encode("utf-8")
    if (
        not provided
        or len(provided_bytes) != len(expected_bytes)
        or not secrets.compare_digest(provided_bytes, expected_bytes)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service credentials",
        )


async def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> str:
    user_id = (x_user_id or "").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-Id header",
        )

    return user_id
