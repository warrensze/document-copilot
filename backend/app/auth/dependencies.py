from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database.supabase import create_admin_client

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    supabase = create_admin_client()
    try:
        user = supabase.auth.get_user(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user.user.model_dump()
