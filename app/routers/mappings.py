from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.issue_mapping import IssueMapping


router = APIRouter(
    prefix="/mappings",
    tags=["Mappings"],
)


@router.get("")
def list_mappings(
    db: Session = Depends(get_db),
):
    mappings = (
        db.query(IssueMapping)
        .order_by(IssueMapping.id.desc())
        .all()
    )

    return {
        "count": len(mappings),
        "mappings": [
            {
                "id": mapping.id,
                "gitlab_project_id": mapping.gitlab_project_id,
                "gitlab_project_name": mapping.gitlab_project_name,
                "gitlab_issue_id": mapping.gitlab_issue_id,
                "gitlab_issue_iid": mapping.gitlab_issue_iid,
                "gitlab_issue_url": mapping.gitlab_issue_url,
                "gitlab_title": mapping.gitlab_title,
                "huly_project_id": mapping.huly_project_id,
                "huly_issue_id": mapping.huly_issue_id,
                "huly_identifier": mapping.huly_identifier,
                "created_at": str(mapping.created_at),
            }
            for mapping in mappings
        ],
    }