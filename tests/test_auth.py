import uuid


def test_signup_and_login_roundtrip(client):
    email = f"test+{uuid.uuid4().hex[:10]}@oricalcum.test"
    password = "Test-Passw0rd!42"

    r = client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    user_id = data["id"]
    assert data["email"] == email

    try:
        # duplicate signup -> 409
        dup = client.post("/api/v1/auth/signup", json={"email": email, "password": password})
        assert dup.status_code == 409, dup.text

        # login returns a usable token
        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        token = login.json()["data"]["access_token"]
        assert token

        # token is accepted by a protected endpoint
        me = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text
    finally:
        from conftest import _delete_account
        _delete_account(user_id)


def test_login_bad_credentials(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@oricalcum.test", "password": "wrong"},
    )
    assert r.status_code == 401


def test_protected_requires_auth(client):
    # no Authorization header -> HTTPBearer rejects with 403
    r = client.get("/api/v1/projects")
    assert r.status_code == 403

    # malformed token -> our handler returns 401
    bad = client.get("/api/v1/projects", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert bad.status_code == 401
