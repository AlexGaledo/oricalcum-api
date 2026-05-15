"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("collaborators", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("settings", JSONB(), nullable=False, server_default="{}"),
        sa.Column("camera", JSONB(), nullable=False, server_default='{"x":0,"y":0,"zoom":1}'),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    op.create_table(
        "nodes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("w", sa.Float(), nullable=False),
        sa.Column("h", sa.Float(), nullable=False),
        sa.Column("base_w", sa.Float(), nullable=False),
        sa.Column("base_h", sa.Float(), nullable=False),
        sa.Column("shape", sa.String(), nullable=False, server_default="rectangle"),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("opacity", sa.Float(), nullable=True),
        sa.Column("tags", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_nodes_project_id", "nodes", ["project_id"])

    op.create_table(
        "edges",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_node", sa.String(), nullable=False),
        sa.Column("to_node", sa.String(), nullable=False),
        sa.Column("from_port", sa.String(), nullable=False, server_default="right"),
        sa.Column("to_port", sa.String(), nullable=False, server_default="left"),
        sa.Column("animation_style", sa.String(), nullable=True),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_edges_project_id", "edges", ["project_id"])

    op.create_table(
        "documents",
        sa.Column("node_id", sa.String(), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    op.create_table(
        "snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_snapshots_project_id", "snapshots", ["project_id"])


def downgrade() -> None:
    op.drop_table("snapshots")
    op.drop_table("documents")
    op.drop_table("edges")
    op.drop_table("nodes")
    op.drop_table("projects")
