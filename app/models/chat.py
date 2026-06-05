from pydantic import BaseModel, Field


class NodespaceContext(BaseModel):
    """Client-supplied awareness of the explorer's nodespaces (files). Only the
    active nodespace's nodes are loaded server-side; the rest are names only."""

    active: str | None = None
    names: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    context: NodespaceContext | None = None


class ChatMessageModel(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str
    content: str
    created_at: int
