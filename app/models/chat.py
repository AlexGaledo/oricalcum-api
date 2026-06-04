from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatMessageModel(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str
    content: str
    created_at: int
