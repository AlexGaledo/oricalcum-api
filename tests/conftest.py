"""Pytest fixtures for the Oricalcum API suite.

Strategy (per the approved test plan):
- Hits the REAL Supabase Postgres via the app's real `get_db` (no DB override).
- Uses REAL Supabase auth: a throwaway account is created once, signed in, and
  its real JWT is reused across the suite. No fake-user dependency override.
- All created rows are uuid-scoped and torn down (project delete cascades to
  child nodes/edges/snapshots). Test accounts use a `test+` email prefix.
"""

import time
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from gotrue.errors import AuthRetryableError
from supabase import create_client

from app.config import get_settings
from app.main import create_app

# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

_settings = get_settings()
# Admin client — service role. NEVER sign in on this one (sign-in mutates the
# Authorization header and would strip admin rights).
_admin = create_client(_settings.supabase_url, _settings.supabase_service_key)


def _retry(fn: Callable, attempts: int = 3, delay: float = 1.0):
    """Absorb the intermittent gotrue 'getaddrinfo failed' (flaky resolver)."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except AuthRetryableError as e:  # network / DNS blip
            last = e
            time.sleep(delay)
    if last:
        raise last
    return fn()


def _create_account() -> dict:
    """Create a confirmed Supabase account, sign in, return id/email/token/headers."""
    email = f"test+{uuid.uuid4().hex[:10]}@oricalcum.test"
    password = "Test-Passw0rd!42"
    created = _retry(
        lambda: _admin.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        )
    )
    user_id = created.user.id
    # Fresh signer client so we don't pollute the admin client's session.
    signer = create_client(_settings.supabase_url, _settings.supabase_service_key)
    session = _retry(
        lambda: signer.auth.sign_in_with_password({"email": email, "password": password})
    )
    token = session.session.access_token
    return {
        "id": user_id,
        "email": email,
        "password": password,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def _delete_account(user_id: str) -> None:
    try:
        _admin.auth.admin.delete_user(user_id)
    except Exception:  # best-effort cleanup
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(scope="session")
def auth_account():
    """Primary test account + real JWT, reused across the suite."""
    acct = _create_account()
    yield acct
    _delete_account(acct["id"])


@pytest.fixture(scope="session")
def second_account():
    """A second real account for ownership / 403 tests."""
    acct = _create_account()
    yield acct
    _delete_account(acct["id"])


@pytest.fixture
def auth_headers(auth_account) -> dict:
    return auth_account["headers"]


@pytest.fixture
def project(client: TestClient, auth_headers: dict):
    """Create a project owned by auth_account; delete it (cascade) on teardown."""
    pid = f"p_{uuid.uuid4().hex[:12]}"
    resp = client.post(
        "/api/v1/projects",
        json={"id": pid, "name": "Test Project", "description": "fixture"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    yield resp.json()["data"]
    client.delete(f"/api/v1/projects/{pid}", headers=auth_headers)


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def now_ms() -> int:
    return int(time.time() * 1000)


def node_payload(node_id: str | None = None, **overrides) -> dict:
    ts = now_ms()
    body = {
        "id": node_id or f"n_{uuid.uuid4().hex[:12]}",
        "x": 10.0, "y": 20.0, "w": 200.0, "h": 120.0,
        "base_w": 200.0, "base_h": 120.0,
        "shape": "rectangle", "title": "Node", "body": "<p>hi</p>",
        "color": None, "opacity": None, "tags": [], "status": "active",
        "version": 1, "created_at": ts, "updated_at": ts,
    }
    body.update(overrides)
    return body


def edge_payload(edge_id: str | None = None, *, from_node: str, to_node: str, **overrides) -> dict:
    body = {
        "id": edge_id or f"e_{uuid.uuid4().hex[:12]}",
        "from_node": from_node, "to_node": to_node,
        "from_port": "right", "to_port": "left",
        "animation_style": None, "label": None,
        "metadata": {}, "version": 1,
    }
    body.update(overrides)
    return body
