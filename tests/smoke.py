"""HTTP smoke test — pings every endpoint of a RUNNING server.

Usage:
    # start the server first, then:
    uv run python tests/smoke.py
    # or against a deployed instance:
    API_BASE=https://host/api/v1 uv run python tests/smoke.py

Distinct from the pytest suite: no DB introspection, just "is every route alive
and returning 2xx". Creates a temp account + project and tears them down at the end.
Exit code 0 if all green, 1 otherwise.
"""

import os
import sys
import time
import uuid
from pathlib import Path

import httpx

# allow `uv run python tests/smoke.py` from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth_client import auth_client  # noqa: E402

API_BASE = os.environ.get("API_BASE", "http://localhost:3001/api/v1")

results: list[tuple[str, str, int, bool]] = []
_token: str | None = None


def now_ms() -> int:
    return int(time.time() * 1000)


def call(label: str, method: str, path: str, *, auth: bool = True, **kw) -> httpx.Response:
    headers = kw.pop("headers", {})
    if auth and _token:
        headers["Authorization"] = f"Bearer {_token}"
    resp = httpx.request(method, f"{API_BASE}{path}", headers=headers, timeout=30, **kw)
    ok = 200 <= resp.status_code < 300
    results.append((label, f"{method} {path}", resp.status_code, ok))
    return resp


def main() -> int:
    global _token
    email = f"test+smoke{uuid.uuid4().hex[:8]}@oricalcum.test"
    password = "Test-Passw0rd!42"
    user_id: str | None = None

    try:
        # --- auth ---
        r = call("signup", "POST", "/auth/signup", auth=False,
                 json={"email": email, "password": password})
        if r.status_code == 200:
            user_id = r.json()["data"]["id"]
        r = call("login", "POST", "/auth/login", auth=False,
                 json={"email": email, "password": password})
        if r.status_code == 200:
            _token = r.json()["data"]["access_token"]

        # --- projects ---
        pid = f"p_{uuid.uuid4().hex[:12]}"
        call("project.create", "POST", "/projects",
             json={"id": pid, "name": "Smoke", "description": ""})
        call("project.list", "GET", "/projects")
        call("project.get", "GET", f"/projects/{pid}")
        call("project.put", "PUT", f"/projects/{pid}",
             json={"name": "Smoke2", "description": "", "collaborators": [],
                   "settings": {}, "camera": {"x": 1, "y": 1, "zoom": 1}, "is_public": False})
        call("project.patch", "PATCH", f"/projects/{pid}",
             json={"camera": {"x": 2, "y": 2, "zoom": 1}})

        # --- nodes ---
        ts = now_ms()
        a = {"id": f"n_{uuid.uuid4().hex[:10]}", "x": 0, "y": 0, "w": 100, "h": 80,
             "base_w": 100, "base_h": 80, "shape": "rectangle", "title": "A", "body": "",
             "color": None, "opacity": None, "tags": [], "status": "active",
             "version": 1, "created_at": ts, "updated_at": ts}
        b = {**a, "id": f"n_{uuid.uuid4().hex[:10]}", "title": "B"}
        call("node.create", "POST", f"/projects/{pid}/nodes", json=a)
        call("node.create2", "POST", f"/projects/{pid}/nodes", json=b)
        call("node.list", "GET", f"/projects/{pid}/nodes")
        call("node.get", "GET", f"/projects/{pid}/nodes/{a['id']}")
        call("node.patch", "PATCH", f"/projects/{pid}/nodes/{a['id']}",
             json={"x": 50, "updated_at": now_ms()})
        call("node.put", "PUT", f"/projects/{pid}/nodes/{a['id']}",
             json={**a, "version": 2, "updated_at": now_ms()})

        # --- edges ---
        eid = f"e_{uuid.uuid4().hex[:10]}"
        edge = {"id": eid, "from_node": a["id"], "to_node": b["id"],
                "from_port": "right", "to_port": "left", "animation_style": None,
                "label": None, "metadata": {}, "version": 1}
        call("edge.create", "POST", f"/projects/{pid}/edges", json=edge)
        call("edge.list", "GET", f"/projects/{pid}/edges")
        call("edge.get", "GET", f"/projects/{pid}/edges/{eid}")
        call("edge.patch", "PATCH", f"/projects/{pid}/edges/{eid}", json={"label": "x"})
        call("edge.put", "PUT", f"/projects/{pid}/edges/{eid}",
             json={**edge, "version": 2})

        # --- documents ---
        call("doc.put", "PUT", f"/documents/{a['id']}",
             json={"content": "<p>d</p>", "version": 1})
        call("doc.get", "GET", f"/documents/{a['id']}")
        call("doc.delete", "DELETE", f"/documents/{a['id']}")

        # --- snapshots ---
        sr = call("snapshot.create", "POST", f"/projects/{pid}/snapshots",
                  json={"name": "v1", "data": {"nodes": [a, b], "edges": [edge],
                        "documents": [], "camera": {"x": 0, "y": 0, "zoom": 1}}})
        sid = sr.json()["data"]["id"] if sr.status_code == 200 else None
        call("snapshot.list", "GET", f"/projects/{pid}/snapshots")
        if sid:
            call("snapshot.get", "GET", f"/projects/{pid}/snapshots/{sid}")
            call("snapshot.delete", "DELETE", f"/projects/{pid}/snapshots/{sid}")

        # --- sync (nodes only; /sync/edges is legacy/broken) ---
        call("sync.nodes", "POST", "/sync/nodes",
             json={"project_id": pid, "last_synced_at": 0,
                   "entities": [{**a, "version": 3, "updated_at": now_ms()}]})

        # --- public (after enabling share) ---
        call("project.share", "PATCH", f"/projects/{pid}/share", json={"is_public": True})
        call("public.project", "GET", f"/public/projects/{pid}", auth=False)
        call("public.nodes", "GET", f"/public/projects/{pid}/nodes", auth=False)
        call("public.edges", "GET", f"/public/projects/{pid}/edges", auth=False)

        # --- cleanup ---
        call("project.delete", "DELETE", f"/projects/{pid}")

    finally:
        if user_id:
            try:
                auth_client.auth.admin.delete_user(user_id)
            except Exception:
                pass

    # report
    width = max(len(label) for label, *_ in results)
    print(f"\nSmoke against {API_BASE}\n" + "-" * (width + 30))
    failed = 0
    for label, route, status, ok in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{mark}] {label.ljust(width)}  {status}  {route}")
    total = len(results)
    print("-" * (width + 30))
    print(f"  {total - failed}/{total} passed" + ("" if not failed else f", {failed} FAILED"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
