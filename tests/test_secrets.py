"""Project secrets — encrypted-at-rest, owner-only."""
from app.db.session import SessionLocal
from app.db.models import ProjectSecret


def test_secret_crud_and_reveal(client, project, auth_headers):
    pid = project["id"]

    # create
    r = client.post(
        f"/api/v1/projects/{pid}/secrets",
        json={"key": "OPENAI_API_KEY", "value": "sk-supersecret-123"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    meta = r.json()["data"]
    sid = meta["id"]
    assert meta["key"] == "OPENAI_API_KEY"
    assert "value" not in meta  # list/create metadata never leaks the value

    # list — no values
    lst = client.get(f"/api/v1/projects/{pid}/secrets", headers=auth_headers)
    assert lst.status_code == 200
    assert any(s["id"] == sid for s in lst.json()["data"])
    assert all("value" not in s for s in lst.json()["data"])

    # stored ciphertext != plaintext (encrypted at rest)
    db = SessionLocal()
    try:
        row = db.get(ProjectSecret, sid)
        assert row is not None
        assert row.value_encrypted != "sk-supersecret-123"
        assert "sk-supersecret-123" not in row.value_encrypted
    finally:
        db.close()

    # reveal — owner gets plaintext back
    rev = client.get(f"/api/v1/projects/{pid}/secrets/{sid}/reveal", headers=auth_headers)
    assert rev.status_code == 200
    assert rev.json()["data"]["value"] == "sk-supersecret-123"

    # update value, re-reveal
    up = client.patch(
        f"/api/v1/projects/{pid}/secrets/{sid}",
        json={"value": "sk-rotated-456"},
        headers=auth_headers,
    )
    assert up.status_code == 200
    rev2 = client.get(f"/api/v1/projects/{pid}/secrets/{sid}/reveal", headers=auth_headers)
    assert rev2.json()["data"]["value"] == "sk-rotated-456"

    # delete
    d = client.delete(f"/api/v1/projects/{pid}/secrets/{sid}", headers=auth_headers)
    assert d.status_code == 200
    assert client.get(
        f"/api/v1/projects/{pid}/secrets/{sid}/reveal", headers=auth_headers
    ).status_code == 404


def test_secret_duplicate_key_conflict(client, project, auth_headers):
    pid = project["id"]
    body = {"key": "DUP", "value": "a"}
    assert client.post(f"/api/v1/projects/{pid}/secrets", json=body, headers=auth_headers).status_code == 200
    dup = client.post(f"/api/v1/projects/{pid}/secrets", json=body, headers=auth_headers)
    assert dup.status_code == 409


def test_secrets_owner_only(client, project, auth_headers, second_account):
    """Collaborators (and strangers) cannot touch secrets — owner-only."""
    pid = project["id"]
    other = second_account["headers"]

    r = client.post(
        f"/api/v1/projects/{pid}/secrets",
        json={"key": "PRIVATE", "value": "nope"},
        headers=auth_headers,
    )
    sid = r.json()["data"]["id"]

    # even after being added as a collaborator, secrets stay owner-only
    client.post(
        f"/api/v1/projects/{pid}/collaborators",
        json={"user_id": second_account["id"]},
        headers=auth_headers,
    )

    assert client.get(f"/api/v1/projects/{pid}/secrets", headers=other).status_code == 403
    assert client.get(f"/api/v1/projects/{pid}/secrets/{sid}/reveal", headers=other).status_code == 403
    assert client.post(
        f"/api/v1/projects/{pid}/secrets", json={"key": "X", "value": "y"}, headers=other
    ).status_code == 403
    assert client.delete(f"/api/v1/projects/{pid}/secrets/{sid}", headers=other).status_code == 403
