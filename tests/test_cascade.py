import uuid

from conftest import edge_payload, node_payload


def test_delete_project_cascades(client, auth_headers):
    pid = str(uuid.uuid4())
    client.post(
        "/api/v1/projects",
        json={"id": pid, "name": "Cascade", "description": ""},
        headers=auth_headers,
    )
    a = node_payload(); b = node_payload()
    client.post(f"/api/v1/projects/{pid}/nodes", json=a, headers=auth_headers)
    client.post(f"/api/v1/projects/{pid}/nodes", json=b, headers=auth_headers)
    client.post(
        f"/api/v1/projects/{pid}/edges",
        json=edge_payload(from_node=a["id"], to_node=b["id"]),
        headers=auth_headers,
    )
    client.post(
        f"/api/v1/projects/{pid}/snapshots",
        json={"name": "s", "data": {"nodes": [a, b], "edges": [], "documents": [],
                                     "camera": {"x": 0, "y": 0, "zoom": 1}}},
        headers=auth_headers,
    )

    # delete the project
    assert client.delete(f"/api/v1/projects/{pid}", headers=auth_headers).status_code == 200

    # children are gone: project 404 -> child reads return 404 via assert_project_access
    assert client.get(f"/api/v1/projects/{pid}", headers=auth_headers).status_code == 404
    assert client.get(f"/api/v1/projects/{pid}/nodes", headers=auth_headers).status_code == 404
    assert client.get(f"/api/v1/projects/{pid}/edges", headers=auth_headers).status_code == 404
    assert client.get(f"/api/v1/projects/{pid}/snapshots", headers=auth_headers).status_code == 404
