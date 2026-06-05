import uuid

from conftest import node_payload, now_ms


def _ns_payload(**overrides) -> dict:
    ts = now_ms()
    body = {
        "kind": "file",
        "name": "Graph A",
        "expanded": True,
        "created_at": ts,
        "updated_at": ts,
    }
    body.update(overrides)
    return body


def test_nodespace_crud_and_tree(client, project, auth_headers):
    pid = project["id"]
    base = f"/api/v1/projects/{pid}/nodespaces"

    # create a folder + a file nested under it
    folder = client.post(base, json=_ns_payload(kind="folder", name="Folder"), headers=auth_headers)
    assert folder.status_code == 200, folder.text
    fid = folder.json()["data"]["id"]

    file_ = client.post(base, json=_ns_payload(name="Graph", parent_id=fid), headers=auth_headers)
    assert file_.status_code == 200, file_.text
    nsid = file_.json()["data"]["id"]
    assert file_.json()["data"]["parent_id"] == fid

    # list returns both, each with a (currently empty) coord manifest
    lst = client.get(base, headers=auth_headers)
    data = {x["id"]: x for x in lst.json()["data"]}
    assert fid in data and nsid in data
    assert data[nsid]["nodes"] == []

    # rename + move to root via PATCH
    p = client.patch(
        f"{base}/{nsid}",
        json={"name": "Renamed", "parent_id": None, "updated_at": now_ms()},
        headers=auth_headers,
    )
    assert p.status_code == 200
    assert p.json()["data"]["name"] == "Renamed"
    assert p.json()["data"]["parent_id"] is None

    # delete
    assert client.delete(f"{base}/{nsid}", headers=auth_headers).status_code == 200
    assert client.get(f"{base}/{nsid}", headers=auth_headers).status_code == 404


def test_nodes_scoped_by_nodespace(client, project, auth_headers):
    pid = project["id"]
    ns_base = f"/api/v1/projects/{pid}/nodespaces"
    node_base = f"/api/v1/projects/{pid}/nodes"

    a = client.post(ns_base, json=_ns_payload(name="A"), headers=auth_headers).json()["data"]["id"]
    b = client.post(ns_base, json=_ns_payload(name="B"), headers=auth_headers).json()["data"]["id"]

    na = client.post(node_base, json=node_payload(nodespace_id=a, x=11.0, y=22.0), headers=auth_headers)
    assert na.status_code == 200
    assert na.json()["data"]["nodespace_id"] == a
    client.post(node_base, json=node_payload(nodespace_id=b), headers=auth_headers)

    # filter by nodespace
    only_a = client.get(f"{node_base}?nodespace_id={a}", headers=auth_headers).json()["data"]
    assert len(only_a) == 1 and only_a[0]["nodespace_id"] == a

    # the manifest projects that node's coordinates
    space_a = client.get(f"{ns_base}/{a}", headers=auth_headers).json()["data"]
    assert space_a["nodes"] == [{"id": only_a[0]["id"], "x": 11.0, "y": 22.0}]

    # deleting the nodespace cascades to its nodes
    assert client.delete(f"{ns_base}/{a}", headers=auth_headers).status_code == 200
    assert client.get(f"{node_base}?nodespace_id={a}", headers=auth_headers).json()["data"] == []


def test_nodespace_requires_project_access(client, project, second_account):
    pid = project["id"]
    other = second_account["headers"]
    base = f"/api/v1/projects/{pid}/nodespaces"
    assert client.get(base, headers=other).status_code == 403
    assert client.post(base, json=_ns_payload(), headers=other).status_code == 403


def test_nodespace_missing_404(client, project, auth_headers):
    pid = project["id"]
    assert client.get(
        f"/api/v1/projects/{pid}/nodespaces/{uuid.uuid4()}", headers=auth_headers
    ).status_code == 404
