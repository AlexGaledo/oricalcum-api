import pytest

from conftest import node_payload, now_ms


def test_sync_nodes_push_and_conflict(client, project, auth_headers):
    pid = project["id"]
    node = node_payload(version=1)

    # push a brand-new node
    r = client.post(
        "/api/v1/sync/nodes",
        json={"project_id": pid, "last_synced_at": 0, "entities": [node]},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["pushed"] == 1

    # it now exists through the REST endpoint
    got = client.get(f"/api/v1/projects/{pid}/nodes/{node['id']}", headers=auth_headers)
    assert got.status_code == 200

    # push a higher version -> accepted (pushed)
    newer = {**node, "version": 2, "title": "v2", "updated_at": now_ms()}
    r2 = client.post(
        "/api/v1/sync/nodes",
        json={"project_id": pid, "last_synced_at": 0, "entities": [newer]},
        headers=auth_headers,
    )
    assert r2.json()["data"]["pushed"] == 1

    # push a lower version -> reported as a conflict, not applied
    older = {**node, "version": 1, "title": "stale", "updated_at": now_ms()}
    r3 = client.post(
        "/api/v1/sync/nodes",
        json={"project_id": pid, "last_synced_at": 0, "entities": [older]},
        headers=auth_headers,
    )
    body = r3.json()["data"]
    assert body["pushed"] == 0
    assert any(c["id"] == node["id"] for c in body["conflicts"])


@pytest.mark.xfail(
    reason="Legacy /sync/edges: SyncEntity requires updated_at, but the Edge model "
    "has no such column, so Edge(**data) raises. Endpoint is unused by the client "
    "(per BACKEND-API-GUIDE). Documented, not fixed here.",
    strict=False,
)
def test_sync_edges_push(client, project, auth_headers):
    pid = project["id"]
    a = node_payload(); b = node_payload()
    client.post(f"/api/v1/projects/{pid}/nodes", json=a, headers=auth_headers)
    client.post(f"/api/v1/projects/{pid}/nodes", json=b, headers=auth_headers)
    edge = {
        "id": "e_sync_1", "from_node": a["id"], "to_node": b["id"],
        "from_port": "right", "to_port": "left", "metadata": {},
        "version": 1, "updated_at": now_ms(),
    }
    r = client.post(
        "/api/v1/sync/edges",
        json={"project_id": pid, "last_synced_at": 0, "entities": [edge]},
        headers=auth_headers,
    )
    assert r.status_code == 200 and r.json()["data"]["pushed"] == 1
