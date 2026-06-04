from pydantic import BaseModel


class PresignUploadBody(BaseModel):
    path: str          # relative path within the workspace, e.g. "docs/spec.pdf"
    content_type: str
    size: int


class CreateFolderBody(BaseModel):
    path: str          # relative folder path, e.g. "docs/drafts"


class MoveBody(BaseModel):
    from_path: str
    to_path: str
