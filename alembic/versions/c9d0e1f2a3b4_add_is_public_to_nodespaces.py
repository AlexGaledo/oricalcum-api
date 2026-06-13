"""add is_public to nodespaces

Per-nodespace sharing: each graph can be made public independently of its
project, so a shared link exposes only that nodespace's nodes/edges.

Revision ID: c9d0e1f2a3b4
Revises: b2c3d4e5f6a7
Create Date: 2026-06-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "nodespaces",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("nodespaces", "is_public")
