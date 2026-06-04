"""MCP tools for reading and editing workspace nodes.

A "node" is a card on the canvas. A "task" is just a node whose `status` carries
its workflow state. Create/patch logic mirrors `app/routers/nodes.py` so anything
the agent writes is wire-consistent with what the REST API / frontend expect
(snake_case fields, millisecond timestamps, `version`).
"""

import re
import time
import uuid

from app.db.models import Edge, Node
from app.mcp.context import scoped_session
from app.mcp.oricalcum_mcp import mcp
from app.models.node import NodeShape, NodeStatus
from app.routers.nodes import _to_dict as node_to_dict

# Defaults for agent-created nodes (the LLM rarely supplies geometry).
_DEFAULT_W = 240.0
_DEFAULT_H = 140.0

_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "but",
    "you", "your", "have", "has", "not", "can", "will", "into", "out", "about",
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _tokens(text: str) -> set[str]:
    """Lowercase content words from a string (HTML stripped, stopwords removed)."""
    clean = _TAG_RE.sub(" ", text or "")
    return {w for w in _WORD_RE.findall(clean.lower()) if w not in _STOP}


def _relevance(node: Node, query_tokens: set[str], query_tags: set[str]) -> float:
    """Lexical relevance of a node to the query. Title and tag hits weigh more."""
    if not query_tokens and not query_tags:
        return 0.0
    title_t = _tokens(node.title)
    body_t = _tokens(node.body)
    node_tags = {t.lower() for t in (node.tags or [])}
    score = 0.0
    score += 3.0 * len(query_tokens & title_t)
    score += 1.0 * len(query_tokens & body_t)
    score += 4.0 * len(query_tags & node_tags)
    score += 4.0 * len(query_tokens & node_tags)
    return score


@mcp.tool
def list_nodes() -> list[dict]:
    """List every node in the current workspace. Use this to load context before
    answering questions or deciding what to create/update."""
    with scoped_session() as s:
        nodes = s.db.query(Node).filter(Node.project_id == s.project_id).all()
        return [node_to_dict(n) for n in nodes]


@mcp.tool
def get_node(node_id: str) -> dict:
    """Get a single node by id from the current workspace."""
    with scoped_session() as s:
        node = (
            s.db.query(Node)
            .filter(Node.id == node_id, Node.project_id == s.project_id)
            .first()
        )
        if not node:
            raise ValueError(f"Node '{node_id}' not found in this workspace")
        return node_to_dict(node)


@mcp.tool
def create_node(
    title: str,
    body: str = "",
    shape: NodeShape = "rectangle",
    tags: list[str] | None = None,
    status: NodeStatus = "active",
    x: float = 0.0,
    y: float = 0.0,
    w: float = _DEFAULT_W,
    h: float = _DEFAULT_H,
) -> dict:
    """Create a new node (card) or task on the canvas. A task is a node with a
    meaningful `status`. `body` is rich-text/markdown content. Returns the node.
    After creating, call `connect_nodes` to link it to related nodes."""
    with scoped_session() as s:
        now = _now_ms()
        node = Node(
            id=str(uuid.uuid4()),
            project_id=s.project_id,
            x=x,
            y=y,
            w=w,
            h=h,
            base_w=w,
            base_h=h,
            shape=shape,
            title=title,
            body=body,
            tags=tags or [],
            status=status,
            version=1,
            created_at=now,
            updated_at=now,
        )
        s.db.add(node)
        s.db.commit()
        s.db.refresh(node)
        return node_to_dict(node)


@mcp.tool
def update_node(
    node_id: str,
    title: str | None = None,
    body: str | None = None,
    status: NodeStatus | None = None,
    tags: list[str] | None = None,
    shape: NodeShape | None = None,
    x: float | None = None,
    y: float | None = None,
) -> dict:
    """Update specific fields of an existing node. Only the arguments you pass are
    changed (patch semantics). Returns the updated node."""
    patch = {
        "title": title,
        "body": body,
        "status": status,
        "tags": tags,
        "shape": shape,
        "x": x,
        "y": y,
    }
    patch = {k: v for k, v in patch.items() if v is not None}
    if not patch:
        raise ValueError("No fields provided to update")
    with scoped_session() as s:
        node = (
            s.db.query(Node)
            .filter(Node.id == node_id, Node.project_id == s.project_id)
            .first()
        )
        if not node:
            raise ValueError(f"Node '{node_id}' not found in this workspace")
        for field, value in patch.items():
            setattr(node, field, value)
        node.version = (node.version or 1) + 1
        node.updated_at = _now_ms()
        s.db.commit()
        s.db.refresh(node)
        return node_to_dict(node)


@mcp.tool
def find_related_nodes(
    query: str,
    tags: list[str] | None = None,
    limit: int = 5,
    exclude_node_ids: list[str] | None = None,
) -> list[dict]:
    """Find existing nodes most related to `query` text (and optional `tags`),
    ranked by lexical overlap of title, body, and tags. Each result includes the
    node's geometry (x, y, w, h) and a `relevance` score, so you can place a new
    node near its related context and connect them. Returns only nodes with a
    non-zero score, best first. Use this BEFORE creating a node to decide where to
    put it and what to connect it to."""
    query_tokens = _tokens(query)
    query_tags = {t.lower() for t in (tags or [])}
    exclude = set(exclude_node_ids or [])
    with scoped_session() as s:
        nodes = s.db.query(Node).filter(Node.project_id == s.project_id).all()
        scored = []
        for n in nodes:
            if n.id in exclude:
                continue
            score = _relevance(n, query_tokens, query_tags)
            if score > 0:
                scored.append((score, n))
        scored.sort(key=lambda p: p[0], reverse=True)
        return [{**node_to_dict(n), "relevance": score} for score, n in scored[:limit]]


@mcp.tool
def create_summary_node(
    title: str,
    body: str,
    source_node_ids: list[str],
    shape: NodeShape = "document",
    tags: list[str] | None = None,
    connect: bool = True,
) -> dict:
    """Create a summary/synthesis node from existing nodes and place it next to
    them. The new node is positioned just above the centroid of its sources and
    (when `connect` is true) linked to each source with an edge — building a small
    "second brain" cluster. Use this after summarizing a set of related nodes.
    `body` is your written summary (rich-text/markdown). Returns the new node and
    the ids of the edges created."""
    if not source_node_ids:
        raise ValueError("source_node_ids must contain at least one node id")
    with scoped_session() as s:
        sources = (
            s.db.query(Node)
            .filter(Node.id.in_(source_node_ids), Node.project_id == s.project_id)
            .all()
        )
        if not sources:
            raise ValueError("None of the source nodes were found in this workspace")

        # Place above the cluster, centered on its horizontal centroid.
        center_x = sum(n.x + n.w / 2 for n in sources) / len(sources)
        top_y = min(n.y for n in sources)
        w, h = _DEFAULT_W, _DEFAULT_H
        x = center_x - w / 2
        y = top_y - h - 80

        now = _now_ms()
        summary = Node(
            id=str(uuid.uuid4()),
            project_id=s.project_id,
            x=x,
            y=y,
            w=w,
            h=h,
            base_w=w,
            base_h=h,
            shape=shape,
            title=title,
            body=body,
            tags=tags or [],
            status="active",
            version=1,
            created_at=now,
            updated_at=now,
        )
        s.db.add(summary)
        s.db.flush()  # assign summary.id before wiring edges

        edge_ids: list[str] = []
        if connect:
            for n in sources:
                edge = Edge(
                    id=str(uuid.uuid4()),
                    project_id=s.project_id,
                    from_node=summary.id,
                    to_node=n.id,
                    from_port="bottom",
                    to_port="top",
                    animation_style=None,
                    label=None,
                    metadata_={},
                    version=1,
                )
                s.db.add(edge)
                edge_ids.append(edge.id)

        s.db.commit()
        s.db.refresh(summary)
        return {"node": node_to_dict(summary), "edge_ids": edge_ids}
