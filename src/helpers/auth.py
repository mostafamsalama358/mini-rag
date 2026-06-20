from fastapi import FastAPI, APIRouter, Depends, status, Header, HTTPException
from helpers.config import get_settings


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
