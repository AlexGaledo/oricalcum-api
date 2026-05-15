from pydantic import BaseModel


class DocumentUpsert(BaseModel):
    content: str
    version: int


class DocumentModel(BaseModel):
    node_id: str
    content: str
    version: int
    created_at: int
    updated_at: int
