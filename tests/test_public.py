from conftest import edge_payload, node_payload


def test_public_gated_by_is_public(client, project, auth_headers):
    pid = project["id"]
    a = node_payload(); b = node_payload()
    client.post(f"/api/v1/projects/{pid}/nodes", json=a, headers=auth_headers)
    client.post(f"/api/v1/projects/{pid}/nodes", json=b, headers=auth_headers)
    client.post(
        f"/api/v1/projects/{pid}/edges",
        json=edge_payload(from_node=a["id"], to_node=b["id"]),
        headers=auth_headers,
    )

    # private -> public reads 404 (no auth header)
    assert client.get(f"/api/v1/public/projects/{pid}").status_code == 404
    assert client.get(f"/api/v1/public/projects/{pid}/nodes").status_code == 404
    assert client.get(f"/api/v1/public/projects/{pid}/edges").status_code == 404

    # make public
    client.patch(f"/api/v1/projects/{pid}/share", json={"is_public": True}, headers=auth_headers)

    # now readable WITHOUT auth
    p = client.get(f"/api/v1/public/projects/{pid}")
    assert p.status_code == 200 and p.json()["data"]["id"] == pid
    nodes = client.get(f"/api/v1/public/projects/{pid}/nodes")
    assert len(nodes.json()["data"]) == 2
    edges = client.get(f"/api/v1/public/projects/{pid}/edges")
    assert len(edges.json()["data"]) == 1

    # toggle off -> 404 again
    client.patch(f"/api/v1/projects/{pid}/share", json={"is_public": False}, headers=auth_headers)
    assert client.get(f"/api/v1/public/projects/{pid}").status_code == 404
