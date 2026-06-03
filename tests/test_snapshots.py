import uuid

from conftest import edge_payload, node_payload


def test_snapshot_lifecycle(client, project, auth_headers):
    pid = project["id"]
    base = f"/api/v1/projects/{pid}/snapshots"

    a = node_payload(); b = node_payload()
    edge = edge_payload(from_node=a["id"], to_node=b["id"])
    snap_data = {
        "nodes": [a, b],
        "edges": [edge],
        "documents": [],
        "camera": {"x": 5, "y": 5, "zoom": 1.5},
    }

    # create
    r = client.post(base, json={"name": "v1", "data": snap_data}, headers=auth_headers)
    assert r.status_code == 200, r.text
    created = r.json()["data"]
    sid = created["id"]
    assert created["name"] == "v1"
    assert created["data"]["camera"] == {"x": 5, "y": 5, "zoom": 1.5}
    assert len(created["data"]["nodes"]) == 2

    # list (no data payload in list items)
    lst = client.get(base, headers=auth_headers)
    assert any(s["id"] == sid for s in lst.json()["data"])

    # get with data
    g = client.get(f"{base}/{sid}", headers=auth_headers)
    assert g.status_code == 200
    assert len(g.json()["data"]["data"]["edges"]) == 1

    # delete
    assert client.delete(f"{base}/{sid}", headers=auth_headers).status_code == 200
    assert client.get(f"{base}/{sid}", headers=auth_headers).status_code == 404


def test_snapshot_missing_404(client, project, auth_headers):
    pid = project["id"]
    assert client.get(
        f"/api/v1/projects/{pid}/snapshots/{uuid.uuid4()}", headers=auth_headers
    ).status_code == 404
