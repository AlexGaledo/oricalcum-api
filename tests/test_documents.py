import uuid

from conftest import node_payload


def test_document_roundtrip(client, project, auth_headers):
    """Documents endpoints are still wired server-side (client stores body on
    the node instead, but the API must keep working)."""
    pid = project["id"]
    node = node_payload()
    client.post(f"/api/v1/projects/{pid}/nodes", json=node, headers=auth_headers)
    nid = node["id"]

    # missing -> 404
    assert client.get(f"/api/v1/documents/{nid}", headers=auth_headers).status_code == 404

    # PUT creates
    up = client.put(
        f"/api/v1/documents/{nid}",
        json={"content": "<h1>doc</h1>", "version": 1},
        headers=auth_headers,
    )
    assert up.status_code == 200
    assert up.json()["data"]["content"] == "<h1>doc</h1>"

    # GET returns it
    g = client.get(f"/api/v1/documents/{nid}", headers=auth_headers)
    assert g.status_code == 200 and g.json()["data"]["version"] == 1

    # PUT updates (upsert)
    up2 = client.put(
        f"/api/v1/documents/{nid}",
        json={"content": "<h1>doc2</h1>", "version": 2},
        headers=auth_headers,
    )
    assert up2.json()["data"]["content"] == "<h1>doc2</h1>"
    assert up2.json()["data"]["version"] == 2

    # DELETE
    assert client.delete(f"/api/v1/documents/{nid}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/v1/documents/{nid}", headers=auth_headers).status_code == 404


def test_document_delete_missing_404(client, auth_headers):
    assert client.delete(
        f"/api/v1/documents/n_{uuid.uuid4().hex}", headers=auth_headers
    ).status_code == 404
