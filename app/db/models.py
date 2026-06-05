from sqlalchemy import BigInteger, Boolean, Column, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from app.db.base import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    start = Column(BigInteger, nullable=False)
    end = Column(BigInteger, nullable=False)
    all_day = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    color = Column(String, nullable=True)
    url = Column(String, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    owner_id = Column(String, nullable=False, index=True)
    collaborators = Column(ARRAY(String), default=[])
    settings = Column(JSONB, default={})
    camera = Column(JSONB, default={"x": 0, "y": 0, "zoom": 1})
    is_public = Column(Boolean, nullable=False, server_default="false", default=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class Nodespace(Base):
    """A graph/file inside a project. Folders nest via parent_id; files own nodes/edges.

    The lightweight coordinate "manifest" (id/title/node positions) is NOT stored
    here — it is projected from the nodes table on read. This keeps the nodes table
    the single source of truth while still letting the explorer load layouts fast.
    """
    __tablename__ = "nodespaces"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String, ForeignKey("nodespaces.id", ondelete="CASCADE"), nullable=True, index=True)
    kind = Column(String, nullable=False, default="file")  # "file" | "folder"
    name = Column(String, nullable=False, default="untitled")
    expanded = Column(Boolean, default=True)
    sort = Column(Float, default=0)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class Node(Base):
    __tablename__ = "nodes"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    nodespace_id = Column(String, ForeignKey("nodespaces.id", ondelete="CASCADE"), nullable=True, index=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    w = Column(Float, nullable=False)
    h = Column(Float, nullable=False)
    base_w = Column(Float, nullable=False)
    base_h = Column(Float, nullable=False)
    shape = Column(String, default="rectangle")
    title = Column(String, default="")
    body = Column(Text, default="")
    color = Column(String, nullable=True)
    opacity = Column(Float, nullable=True)
    tags = Column(ARRAY(String), default=[])
    status = Column(String, default="active")
    version = Column(Integer, default=1)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class Edge(Base):
    __tablename__ = "edges"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    nodespace_id = Column(String, ForeignKey("nodespaces.id", ondelete="CASCADE"), nullable=True, index=True)
    from_node = Column(String, nullable=False)
    to_node = Column(String, nullable=False)
    from_port = Column(String, default="right")
    to_port = Column(String, default="left")
    animation_style = Column(String, nullable=True)
    label = Column(String, nullable=True)
    metadata_ = Column("metadata", JSONB, default={})
    version = Column(Integer, default=1)


class Document(Base):
    __tablename__ = "documents"

    node_id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class ProjectSecret(Base):
    __tablename__ = "project_secrets"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_project_secret_key"),)

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String, nullable=False)
    value_encrypted = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(String, nullable=False)
    name = Column(String, default="")
    data = Column(JSONB, nullable=False)
    created_at = Column(BigInteger, nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)
