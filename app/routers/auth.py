from fastapi import APIRouter, HTTPException
from gotrue.errors import AuthApiError
from supabase import create_client
from app.auth_client import auth_client
from app.config import get_settings
from app.models.auth import LoginRequest, SignupRequest
from app.schemas.response import ok

router = APIRouter(prefix="/auth", tags=["auth"])


def _fresh_client():
    # A throwaway client for sign-in. sign_in_with_password mutates the client's
    # Authorization header to the user JWT, so we must NOT reuse the shared
    # admin `auth_client` here — that would strip its service-role rights.
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_key)


@router.post("/signup")
async def signup(body: SignupRequest):
    """Create a Supabase auth account (admin, email pre-confirmed).

    Used by the test suite to mint real accounts. Returns the new user id/email.
    """
    try:
        response = auth_client.auth.admin.create_user(
            {
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
            }
        )
    except AuthApiError as e:
        # duplicate email / weak password / etc.
        status = 409 if "already" in str(e).lower() else 400
        raise HTTPException(status_code=status, detail=str(e))

    user = response.user
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create user")
    return ok({"id": user.id, "email": user.email})


@router.post("/login")
async def login(body: LoginRequest):
    """Sign in with email/password, returning a usable JWT access token."""
    try:
        response = _fresh_client().auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as e:
        raise HTTPException(status_code=401, detail=str(e))

    session = response.session
    user = response.user
    if not session or not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return ok({
        "access_token": session.access_token,
        "user_id": user.id,
        "email": user.email,
    })
