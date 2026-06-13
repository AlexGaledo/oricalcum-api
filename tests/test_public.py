from conftest import edge_payload, node_payload, now_ms


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


def _ns(name: str) -> dict:
    ts = now_ms()
    return {"kind": "file", "name": name, "expanded": True, "created_at": ts, "updated_at": ts}


def test_public_nodespace_scopes_to_one_graph(client, project, auth_headers):
    pid = project["id"]
    ns_base = f"/api/v1/projects/{pid}/nodespaces"
    node_base = f"/api/v1/projects/{pid}/nodes"
    edge_base = f"/api/v1/projects/{pid}/edges"

    a = client.post(ns_base, json=_ns("A"), headers=auth_headers).json()["data"]["id"]
    b = client.post(ns_base, json=_ns("B"), headers=auth_headers).json()["data"]["id"]

    # two nodes + an edge in A; one node in B
    a1 = node_payload(nodespace_id=a); a2 = node_payload(nodespace_id=a)
    client.post(node_base, json=a1, headers=auth_headers)
    client.post(node_base, json=a2, headers=auth_headers)
    client.post(
        edge_base,
        json=edge_payload(from_node=a1["id"], to_node=a2["id"], nodespace_id=a),
        headers=auth_headers,
    )
    client.post(node_base, json=node_payload(nodespace_id=b), headers=auth_headers)

    # private -> 404 without auth
    assert client.get(f"/api/v1/public/nodespaces/{a}").status_code == 404

    # share A only
    share = client.patch(f"{ns_base}/{a}/share", json={"is_public": True}, headers=auth_headers)
    assert share.status_code == 200 and share.json()["data"]["is_public"] is True

    # A is public and scoped to ONLY its own nodes/edges
    meta = client.get(f"/api/v1/public/nodespaces/{a}")
    assert meta.status_code == 200 and meta.json()["data"]["id"] == a
    nodes = client.get(f"/api/v1/public/nodespaces/{a}/nodes").json()["data"]
    assert len(nodes) == 2
    edges = client.get(f"/api/v1/public/nodespaces/{a}/edges").json()["data"]
    assert len(edges) == 1

    # B was never shared -> still 404 (no sibling-graph leakage)
    assert client.get(f"/api/v1/public/nodespaces/{b}").status_code == 404
    assert client.get(f"/api/v1/public/nodespaces/{b}/nodes").status_code == 404

    # toggle A off -> 404 again
    client.patch(f"{ns_base}/{a}/share", json={"is_public": False}, headers=auth_headers)
    assert client.get(f"/api/v1/public/nodespaces/{a}").status_code == 404
