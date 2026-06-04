"""MCP tools for reading and editing edges (connections between nodes).

Mirrors `app/routers/edges.py` so anything the agent writes is wire-consistent
with the REST API / frontend (snake_case, ports, version). Lets the assistant
wire related ideas together — part of the in-canvas "reasoning" loop.
"""

import uuid

from app.db.models import Edge, Node
from app.mcp.context import scoped_session
from app.mcp.oricalcum_mcp import mcp
from app.models.edge import AnimationStyle, Port
from app.routers.edges import _to_dict as edge_to_dict


def _node_exists(s, node_id: str) -> bool:
    return (
        s.db.query(Node)
        .filter(Node.id == node_id, Node.project_id == s.project_id)
        .first()
        is not None
    )


@mcp.tool
def list_edges() -> list[dict]:
    """List every edge (connection) in the current workspace. Use this to see how
    nodes are already related before connecting or disconnecting them."""
    with scoped_session() as s:
        edges = s.db.query(Edge).filter(Edge.project_id == s.project_id).all()
        return [edge_to_dict(e) for e in edges]


@mcp.tool
def connect_nodes(
    from_node: str,
    to_node: str,
    label: str | None = None,
    from_port: Port = "right",
    to_port: Port = "left",
    animation_style: AnimationStyle | None = None,
) -> dict:
    """Connect two existing nodes with a directed edge (from_node -> to_node).
    Use this to link related ideas, dependencies, or a summary to its sources.
    Both nodes must already exist in this workspace. Idempotent: returns the
    existing edge if the same pair is already connected. Returns the edge."""
    if from_node == to_node:
        raise ValueError("Cannot connect a node to itself")
    with scoped_session() as s:
        if not _node_exists(s, from_node):
            raise ValueError(f"Node '{from_node}' not found in this workspace")
        if not _node_exists(s, to_node):
            raise ValueError(f"Node '{to_node}' not found in this workspace")

        existing = (
            s.db.query(Edge)
            .filter(
                Edge.project_id == s.project_id,
                Edge.from_node == from_node,
                Edge.to_node == to_node,
            )
            .first()
        )
        if existing:
            return edge_to_dict(existing)

        edge = Edge(
            id=str(uuid.uuid4()),
            project_id=s.project_id,
            from_node=from_node,
            to_node=to_node,
            from_port=from_port,
            to_port=to_port,
            animation_style=animation_style,
            label=label,
            metadata_={},
            version=1,
        )
        s.db.add(edge)
        s.db.commit()
        s.db.refresh(edge)
        return edge_to_dict(edge)


@mcp.tool
def disconnect_nodes(edge_id: str) -> dict:
    """Delete an edge by id, removing the connection between its two nodes."""
    with scoped_session() as s:
        edge = (
            s.db.query(Edge)
            .filter(Edge.id == edge_id, Edge.project_id == s.project_id)
            .first()
        )
        if not edge:
            raise ValueError(f"Edge '{edge_id}' not found in this workspace")
        s.db.delete(edge)
        s.db.commit()
        return {"deleted": edge_id}
