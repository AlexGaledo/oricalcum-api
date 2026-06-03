import uuid

from conftest import edge_payload, node_payload


def _two_nodes(client, pid, headers):
    a = node_payload(); b = node_payload()
    client.post(f"/api/v1/projects/{pid}/nodes", json=a, headers=headers)
    client.post(f"/api/v1/projects/{pid}/nodes", json=b, headers=headers)
    return a["id"], b["id"]


def test_edge_crud(client, project, auth_headers):
    pid = project["id"]
    base = f"/api/v1/projects/{pid}/edges"
    a, b = _two_nodes(client, pid, auth_headers)

    payload = edge_payload(from_node=a, to_node=b, metadata={"k": "v"})
    r = client.post(base, json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    e = r.json()["data"]
    eid = payload["id"]
    assert e["from_node"] == a and e["to_node"] == b
    # metadata round-trips through the metadata_ column alias
    assert e["metadata"] == {"k": "v"}

    # duplicate id -> 409
    assert client.post(base, json=payload, headers=auth_headers).status_code == 409

    # list / get
    assert any(x["id"] == eid for x in client.get(base, headers=auth_headers).json()["data"])
    assert client.get(f"{base}/{eid}", headers=auth_headers).json()["data"]["id"] == eid

    # PATCH (re-port + label)
    p = client.patch(
        f"{base}/{eid}", json={"to_port": "top", "label": "rel"}, headers=auth_headers
    )
    assert p.json()["data"]["to_port"] == "top" and p.json()["data"]["label"] == "rel"

    # PUT full replace
    put = client.put(
        f"{base}/{eid}",
        json=edge_payload(eid, from_node=a, to_node=b, from_port="bottom",
                          to_port="top", metadata={"x": 1}, version=2),
        headers=auth_headers,
    )
    assert put.status_code == 200 and put.json()["data"]["from_port"] == "bottom"

    # delete
    assert client.delete(f"{base}/{eid}", headers=auth_headers).status_code == 200
    assert client.get(f"{base}/{eid}", headers=auth_headers).status_code == 404


def test_edge_missing_404(client, project, auth_headers):
    pid = project["id"]
    assert client.get(
        f"/api/v1/projects/{pid}/edges/e_{uuid.uuid4().hex}", headers=auth_headers
    ).status_code == 404


def test_edge_requires_project_access(client, project, second_account):
    pid = project["id"]
    other = second_account["headers"]
    assert client.get(f"/api/v1/projects/{pid}/edges", headers=other).status_code == 403
