"""add_nodespaces

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-05 12:00:00.000000

Adds the `nodespaces` table (a graph/file inside a project) and a nullable
`nodespace_id` FK on `nodes` and `edges`. Backfills one default nodespace per
existing project and assigns that project's existing nodes/edges to it, so
current canvases keep loading.
"""
import time
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'nodespaces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('parent_id', sa.String(), nullable=True),
        sa.Column('kind', sa.String(), nullable=False, server_default='file'),
        sa.Column('name', sa.String(), nullable=False, server_default='untitled'),
        sa.Column('expanded', sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column('sort', sa.Float(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['nodespaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_nodespaces_project_id'), 'nodespaces', ['project_id'], unique=False)
    op.create_index(op.f('ix_nodespaces_parent_id'), 'nodespaces', ['parent_id'], unique=False)

    op.add_column('nodes', sa.Column('nodespace_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_nodes_nodespace_id'), 'nodes', ['nodespace_id'], unique=False)
    op.create_foreign_key(
        'fk_nodes_nodespace_id', 'nodes', 'nodespaces',
        ['nodespace_id'], ['id'], ondelete='CASCADE',
    )

    op.add_column('edges', sa.Column('nodespace_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_edges_nodespace_id'), 'edges', ['nodespace_id'], unique=False)
    op.create_foreign_key(
        'fk_edges_nodespace_id', 'edges', 'nodespaces',
        ['nodespace_id'], ['id'], ondelete='CASCADE',
    )

    _backfill_default_nodespaces()


def _backfill_default_nodespaces() -> None:
    """Create one 'untitled' nodespace per project and adopt its nodes/edges."""
    conn = op.get_bind()
    now = int(time.time() * 1000)
    projects = conn.execute(sa.text("SELECT id FROM projects")).fetchall()
    for (project_id,) in projects:
        nsid = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO nodespaces "
                "(id, project_id, parent_id, kind, name, expanded, sort, created_at, updated_at) "
                "VALUES (:id, :pid, NULL, 'file', 'untitled', true, 0, :now, :now)"
            ),
            {"id": nsid, "pid": project_id, "now": now},
        )
        conn.execute(
            sa.text("UPDATE nodes SET nodespace_id = :nsid WHERE project_id = :pid"),
            {"nsid": nsid, "pid": project_id},
        )
        conn.execute(
            sa.text("UPDATE edges SET nodespace_id = :nsid WHERE project_id = :pid"),
            {"nsid": nsid, "pid": project_id},
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_edges_nodespace_id', 'edges', type_='foreignkey')
    op.drop_index(op.f('ix_edges_nodespace_id'), table_name='edges')
    op.drop_column('edges', 'nodespace_id')

    op.drop_constraint('fk_nodes_nodespace_id', 'nodes', type_='foreignkey')
    op.drop_index(op.f('ix_nodes_nodespace_id'), table_name='nodes')
    op.drop_column('nodes', 'nodespace_id')

    op.drop_index(op.f('ix_nodespaces_parent_id'), table_name='nodespaces')
    op.drop_index(op.f('ix_nodespaces_project_id'), table_name='nodespaces')
    op.drop_table('nodespaces')
