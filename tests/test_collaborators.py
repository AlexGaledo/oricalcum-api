"""Collaborator add/remove/list endpoints."""
import uuid


def test_collaborator_lifecycle(client, project, auth_headers, second_account):
    pid = project["id"]
    other = second_account["headers"]

    # before: second user has no access
    assert client.get(f"/api/v1/projects/{pid}", headers=other).status_code == 403

    # owner lists collaborators — just the owner, flagged
    lst = client.get(f"/api/v1/projects/{pid}/collaborators", headers=auth_headers)
    assert lst.status_code == 200
    owners = [c for c in lst.json()["data"] if c["is_owner"]]
    assert len(owners) == 1

    # add by email
    add = client.post(
        f"/api/v1/projects/{pid}/collaborators",
        json={"email": second_account["email"]},
        headers=auth_headers,
    )
    assert add.status_code == 200, add.text
    assert second_account["id"] in add.json()["data"]["collaborators"]

    # second user now has read access to the project
    assert client.get(f"/api/v1/projects/{pid}", headers=other).status_code == 200

    # list shows two, second resolved to its email
    lst2 = client.get(f"/api/v1/projects/{pid}/collaborators", headers=auth_headers)
    ids = {c["user_id"] for c in lst2.json()["data"]}
    assert second_account["id"] in ids
    match = next(c for c in lst2.json()["data"] if c["user_id"] == second_account["id"])
    assert match["email"] == second_account["email"]
    assert match["is_owner"] is False

    # remove
    rm = client.delete(
        f"/api/v1/projects/{pid}/collaborators/{second_account['id']}", headers=auth_headers
    )
    assert rm.status_code == 200
    assert second_account["id"] not in rm.json()["data"]["collaborators"]
    assert client.get(f"/api/v1/projects/{pid}", headers=other).status_code == 403


def test_add_collaborator_unknown_email(client, project, auth_headers):
    pid = project["id"]
    r = client.post(
        f"/api/v1/projects/{pid}/collaborators",
        json={"email": f"missing-{uuid.uuid4().hex[:8]}@nowhere.test"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_add_collaborator_requires_owner(client, project, second_account):
    pid = project["id"]
    other = second_account["headers"]
    r = client.post(
        f"/api/v1/projects/{pid}/collaborators",
        json={"user_id": "whoever"},
        headers=other,
    )
    assert r.status_code == 403
