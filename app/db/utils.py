from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models import Project


def assert_project_access(db: Session, project_id: str, user_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    collaborators = project.collaborators or []
    if project.owner_id != user_id and user_id not in collaborators:
        raise HTTPException(status_code=403, detail="Forbidden")
    return project
