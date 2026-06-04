"""Per-request scope + DB session for MCP tools.

Security boundary: an MCP tool must operate as a specific authenticated user on a
specific project. The LLM is never trusted to supply that scope. Instead it comes
from the MCP request headers set by the agent layer for each chat request:

    Authorization: Bearer <supabase_jwt>
    X-Project-Id:  <project_id>

`scoped_session()` validates the JWT (same path as the REST API), asserts the user
can access the project, and yields a (db, user_id, project_id) scope. Tools call it
as a context manager so the DB session is always closed.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from fastmcp.server.dependencies import get_http_headers
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.utils import assert_project_access
from app.dependencies import authenticate_token


class MCPAuthError(Exception):
    """Raised when MCP request headers are missing/invalid. Surfaced to the model
    as a tool error so it can tell the user instead of crashing the stream."""


@dataclass
class Scope:
    db: Session
    user_id: str
    project_id: str


def _resolve_headers() -> tuple[str, str]:
    # include_all=True: FastMCP omits Authorization (and other sensitive headers)
    # by default; we need it to authenticate the caller.
    headers = get_http_headers(include_all=True)
    auth = headers.get("authorization") or headers.get("Authorization")
    project_id = headers.get("x-project-id") or headers.get("X-Project-Id")
    if not auth or not auth.lower().startswith("bearer "):
        raise MCPAuthError("Missing or malformed Authorization header")
    if not project_id:
        raise MCPAuthError("Missing X-Project-Id header")
    return auth.split(" ", 1)[1].strip(), project_id


@contextmanager
def scoped_session() -> Iterator[Scope]:
    """Authenticate the caller, assert project access, yield a scoped DB session."""
    token, project_id = _resolve_headers()
    user = authenticate_token(token)  # raises HTTPException(401) on bad token
    db = SessionLocal()
    try:
        assert_project_access(db, project_id, user["id"])  # raises 403/404
        yield Scope(db=db, user_id=user["id"], project_id=project_id)
    finally:
        db.close()
