import uuid

from conftest import node_payload, now_ms


def test_node_crud(client, project, auth_headers):
    pid = project["id"]
    base = f"/api/v1/projects/{pid}/nodes"
    payload = node_payload(title="Hello", body="<p>body</p>")

    # create
    r = client.post(base, json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    n = r.json()["data"]
    assert n["id"] == payload["id"]
    assert n["base_w"] == 200.0 and n["base_h"] == 120.0
    assert n["body"] == "<p>body</p>"
    assert n["version"] == 1

    nid = payload["id"]

    # duplicate id -> 409
    assert client.post(base, json=payload, headers=auth_headers).status_code == 409

    # list
    lst = client.get(base, headers=auth_headers)
    assert any(x["id"] == nid for x in lst.json()["data"])

    # get one
    assert client.get(f"{base}/{nid}", headers=auth_headers).json()["data"]["id"] == nid

    # PATCH partial (move + retitle)
    p = client.patch(
        f"{base}/{nid}",
        json={"x": 999.0, "title": "Moved", "updated_at": now_ms()},
        headers=auth_headers,
    )
    assert p.status_code == 200
    assert p.json()["data"]["x"] == 999.0 and p.json()["data"]["title"] == "Moved"
    assert p.json()["data"]["y"] == 20.0  # untouched

    # PUT full replace
    put = client.put(
        f"{base}/{nid}",
        json=node_payload(nid, x=1, y=1, w=1, h=1, base_w=1, base_h=1,
                          title="Full", version=2, updated_at=now_ms()),
        headers=auth_headers,
    )
    assert put.status_code == 200 and put.json()["data"]["title"] == "Full"

    # delete
    assert client.delete(f"{base}/{nid}", headers=auth_headers).status_code == 200
    assert client.get(f"{base}/{nid}", headers=auth_headers).status_code == 404


def test_node_bad_body_422(client, project, auth_headers):
    pid = project["id"]
    # missing required numeric fields
    r = client.post(
        f"/api/v1/projects/{pid}/nodes",
        json={"id": "n_bad", "title": "x"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_node_requires_project_access(client, project, second_account):
    pid = project["id"]
    other = second_account["headers"]
    # second user has no access to project -> 403 on list/create
    assert client.get(f"/api/v1/projects/{pid}/nodes", headers=other).status_code == 403
    assert client.post(
        f"/api/v1/projects/{pid}/nodes", json=node_payload(), headers=other
    ).status_code == 403


def test_node_missing_404(client, project, auth_headers):
    pid = project["id"]
    assert client.get(
        f"/api/v1/projects/{pid}/nodes/{uuid.uuid4()}", headers=auth_headers
    ).status_code == 404
