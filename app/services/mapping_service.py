from sqlalchemy.orm import Session

from app.models.issue_mapping import IssueMapping


def find_mapping_by_gitlab(
    db: Session,
    gitlab_project_id: int,
    gitlab_issue_id: int,
) -> IssueMapping | None:
    return (
        db.query(IssueMapping)
        .filter(
            IssueMapping.gitlab_project_id == gitlab_project_id,
            IssueMapping.gitlab_issue_id == gitlab_issue_id,
        )
        .first()
    )


def find_mapping_by_huly(
    db: Session,
    huly_project_id: str,
    huly_issue_id: str,
) -> IssueMapping | None:
    return (
        db.query(IssueMapping)
        .filter(
            IssueMapping.huly_project_id == huly_project_id,
            IssueMapping.huly_issue_id == huly_issue_id,
        )
        .first()
    )


def list_issue_mappings(
    db: Session,
) -> list[IssueMapping]:
    return (
        db.query(IssueMapping)
        .order_by(IssueMapping.id.desc())
        .all()
    )


def serialize_mapping(
    mapping: IssueMapping,
) -> dict:
    return {
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