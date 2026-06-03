import uuid


def test_project_crud(client, auth_headers):
    pid = str(uuid.uuid4())
    # create
    r = client.post(
        "/api/v1/projects",
        json={"id": pid, "name": "Alpha", "description": "first"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    proj = r.json()["data"]
    assert proj["id"] == pid and proj["name"] == "Alpha"
    assert proj["camera"] == {"x": 0, "y": 0, "zoom": 1}

    try:
        # duplicate create is idempotent (returns existing), not 409
        again = client.post(
            "/api/v1/projects",
            json={"id": pid, "name": "ignored", "description": ""},
            headers=auth_headers,
        )
        assert again.status_code == 200
        assert again.json()["data"]["name"] == "Alpha"

        # get
        g = client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
        assert g.status_code == 200 and g.json()["data"]["id"] == pid

        # list includes it
        lst = client.get("/api/v1/projects", headers=auth_headers)
        assert any(p["id"] == pid for p in lst.json()["data"])

        # PUT full replace
        put = client.put(
            f"/api/v1/projects/{pid}",
            json={"name": "Beta", "description": "second", "collaborators": [],
                  "settings": {}, "camera": {"x": 1, "y": 2, "zoom": 3}, "is_public": False},
            headers=auth_headers,
        )
        assert put.status_code == 200
        assert put.json()["data"]["name"] == "Beta"
        assert put.json()["data"]["camera"] == {"x": 1, "y": 2, "zoom": 3}

        # PATCH partial — camera only
        pc = client.patch(
            f"/api/v1/projects/{pid}",
            json={"camera": {"x": 9, "y": 9, "zoom": 2}},
            headers=auth_headers,
        )
        assert pc.status_code == 200
        assert pc.json()["data"]["camera"] == {"x": 9, "y": 9, "zoom": 2}
        assert pc.json()["data"]["name"] == "Beta"  # untouched

        # PATCH partial — name only
        pn = client.patch(
            f"/api/v1/projects/{pid}", json={"name": "Gamma"}, headers=auth_headers
        )
        assert pn.json()["data"]["name"] == "Gamma"
        assert pn.json()["data"]["camera"] == {"x": 9, "y": 9, "zoom": 2}  # untouched
    finally:
        d = client.delete(f"/api/v1/projects/{pid}", headers=auth_headers)
        assert d.status_code == 200

    # gone after delete
    assert client.get(f"/api/v1/projects/{pid}", headers=auth_headers).status_code == 404


def test_share_toggle(client, project, auth_headers):
    pid = project["id"]
    r = client.patch(
        f"/api/v1/projects/{pid}/share", json={"is_public": True}, headers=auth_headers
    )
    assert r.status_code == 200 and r.json()["data"]["is_public"] is True
    off = client.patch(
        f"/api/v1/projects/{pid}/share", json={"is_public": False}, headers=auth_headers
    )
    assert off.json()["data"]["is_public"] is False


def test_project_not_found(client, auth_headers):
    assert client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=auth_headers).status_code == 404


def test_project_forbidden_for_other_user(client, project, second_account):
    pid = project["id"]
    other = second_account["headers"]
    # owner check: second user cannot read/patch/delete
    assert client.get(f"/api/v1/projects/{pid}", headers=other).status_code == 403
    assert client.patch(f"/api/v1/projects/{pid}", json={"name": "x"}, headers=other).status_code == 403
    assert client.delete(f"/api/v1/projects/{pid}", headers=other).status_code == 403
