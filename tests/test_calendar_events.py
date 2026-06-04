import uuid

from conftest import now_ms


def _payload(**overrides) -> dict:
    ts = now_ms()
    body = {
        "title": "Test Event",
        "start": ts,
        "end": ts + 3_600_000,
        "all_day": False,
        "description": "a description",
        "color": "#ff0000",
        "created_at": ts,
        "updated_at": ts,
    }
    body.update(overrides)
    return body


def test_calendar_event_crud(client, project, auth_headers):
    pid = project["id"]
    base = f"/api/v1/projects/{pid}/calendar-events"
    payload = _payload()

    # create
    r = client.post(base, json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    e = r.json()["data"]
    assert e["title"] == "Test Event"
    assert e["start"] == payload["start"]
    assert e["end"] == payload["end"]
    eid = e["id"]

    # list
    lst = client.get(base, headers=auth_headers)
    assert any(x["id"] == eid for x in lst.json()["data"])

    # get one
    g = client.get(f"{base}/{eid}", headers=auth_headers)
    assert g.status_code == 200
    assert g.json()["data"]["id"] == eid

    # PATCH partial (retitle)
    p = client.patch(
        f"{base}/{eid}",
        json={"title": "Updated", "updated_at": now_ms()},
        headers=auth_headers,
    )
    assert p.status_code == 200
    assert p.json()["data"]["title"] == "Updated"
    assert p.json()["data"]["start"] == payload["start"]  # untouched

    # PUT full replace
    ts = now_ms()
    put = client.put(
        f"{base}/{eid}",
        json=_payload(title="Full Replace", start=ts, end=ts + 7_200_000, updated_at=ts),
        headers=auth_headers,
    )
    assert put.status_code == 200
    assert put.json()["data"]["title"] == "Full Replace"
    assert put.json()["data"]["end"] == ts + 7_200_000

    # delete
    assert client.delete(f"{base}/{eid}", headers=auth_headers).status_code == 200
    assert client.get(f"{base}/{eid}", headers=auth_headers).status_code == 404


def test_calendar_event_duplicate_409(client, project, auth_headers):
    pid = project["id"]
    base = f"/api/v1/projects/{pid}/calendar-events"
    payload = _payload(id=str(uuid.uuid4()))

    r1 = client.post(base, json=payload, headers=auth_headers)
    assert r1.status_code == 200

    r2 = client.post(base, json=payload, headers=auth_headers)
    assert r2.status_code == 409


def test_calendar_event_requires_project_access(client, project, second_account):
    pid = project["id"]
    base = f"/api/v1/projects/{pid}/calendar-events"
    other = second_account["headers"]

    assert client.get(base, headers=other).status_code == 403
    assert client.post(base, json=_payload(), headers=other).status_code == 403


def test_calendar_event_missing_404(client, project, auth_headers):
    pid = project["id"]
    fake = str(uuid.uuid4())
    base = f"/api/v1/projects/{pid}/calendar-events"

    assert client.get(f"{base}/{fake}", headers=auth_headers).status_code == 404
    assert client.patch(f"{base}/{fake}", json={"updated_at": now_ms()}, headers=auth_headers).status_code == 404
    assert client.delete(f"{base}/{fake}", headers=auth_headers).status_code == 404
