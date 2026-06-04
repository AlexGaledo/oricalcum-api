from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_auth.errors import AuthApiError
from app.auth_client import auth_client

bearer_scheme = HTTPBearer()


def authenticate_token(token: str) -> dict:
    """Validate a Supabase JWT and return {id, email}.

    Shared by the FastAPI dependency and the MCP tool layer (which authenticates
    from request headers, outside FastAPI's dependency injection).
    """
    try:
        response = auth_client.auth.get_user(token)
        user = response.user
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"id": user.id, "email": user.email}
    except AuthApiError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> dict:
    return authenticate_token(credentials.credentials)


CurrentUser = Annotated[dict, Depends(get_current_user)]
