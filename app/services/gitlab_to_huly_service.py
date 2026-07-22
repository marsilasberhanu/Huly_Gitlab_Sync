from sqlalchemy.orm import Session

from app.clients.huly_adapter_client import (
    HulyAdapterClient,
)
from app.models.issue_mapping import IssueMapping
from app.models.project_link import ProjectLink
from app.services.connected_account_service import (
    get_huly_credentials,
)
from app.services.mapping_service import (
    find_mapping_by_gitlab_for_link,
)


async def sync_gitlab_issue_to_huly(
    *,
    payload: dict,
    gitlab_event: str | None,
    db: Session,
    project_link: ProjectLink,
) -> dict:
    if gitlab_event != "Issue Hook":
        return {
            "status": "ignored",
            "reason": "Not a GitLab Issue Hook",
        }

    if payload.get("object_kind") != "issue":
        return {
            "status": "ignored",
            "reason": "Not an issue event",
        }

    attributes = payload.get(
        "object_attributes",
        {},
    )
    project = payload.get("project", {})
    user = payload.get("user", {})

    gitlab_project_id = project.get("id")
    issue_id = attributes.get("id")
    issue_iid = attributes.get("iid")

    if not gitlab_project_id or not issue_id:
        return {
            "status": "failed",
            "reason": (
                "Missing GitLab project ID "
                "or GitLab issue ID."
            ),
        }

    if (
        int(gitlab_project_id)
        != int(project_link.gitlab_project_id)
    ):
        return {
            "status": "rejected",
            "reason": (
                "Webhook project does not match "
                "the configured project link."
            ),
        }

    issue_action = attributes.get("action")

    if not issue_action:
        issue_action = {
            "opened": "open",
            "closed": "close",
        }.get(
            attributes.get("state"),
            "unknown",
        )

    existing_mapping = (
        find_mapping_by_gitlab_for_link(
            db,
            project_link_id=project_link.id,
            gitlab_issue_id=int(issue_id),
        )
    )

    if existing_mapping:
        return {
            "status": "already_synced",
            "message": (
                "This GitLab issue already has "
                "a Huly issue mapping."
            ),
            "mapping_id": existing_mapping.id,
            "huly_issue_id": (
                existing_mapping.huly_issue_id
            ),
            "huly_identifier": (
                existing_mapping.huly_identifier
            ),
        }

    if issue_action not in {"open", "reopen"}:
        return {
            "status": "ignored",
            "reason": (
                f"Issue action is not handled yet: "
                f"{issue_action}"
            ),
        }

    issue_title = (
        attributes.get("title")
        or "Untitled GitLab issue"
    )
    issue_description = (
        attributes.get("description")
        or "No description provided."
    )

    gitlab_project_name = (
        project.get("name")
        or project_link.gitlab_project_name
        or "Unknown GitLab project"
    )
    gitlab_project_url = project.get("web_url", "")
    issue_url = attributes.get("url", "")
    gitlab_user_name = (
        user.get("name")
        or "Unknown user"
    )

    huly_credentials = get_huly_credentials(
        db,
        user_id=project_link.user_id,
    )

    adapter = HulyAdapterClient()

    huly_result = await adapter.create_issue(
        credentials=huly_credentials,
        payload={
            "projectId": project_link.huly_project_id,
            "title": issue_title,
            "description": f"""
Created from GitLab.

GitLab Project: {gitlab_project_name}
GitLab Project URL: {gitlab_project_url}
GitLab Project ID: {gitlab_project_id}
GitLab Issue ID: {issue_id}
GitLab Issue IID: {issue_iid}
GitLab Issue URL: {issue_url}
Triggered by: {gitlab_user_name}

Original GitLab Description:
{issue_description}
""".strip(),
            "issueType": "Issue",
            "priority": 2,
        },
    )

    huly_issue_id = (
        huly_result.get("issueId")
        or huly_result.get("result")
    )
    huly_identifier = huly_result.get("identifier")

    if not huly_issue_id:
        raise RuntimeError(
            "Huly adapter response did not contain "
            "a Huly issue ID."
        )

    mapping = IssueMapping(
        user_id=project_link.user_id,
        project_link_id=project_link.id,

        gitlab_project_id=int(gitlab_project_id),
        gitlab_project_name=gitlab_project_name,

        gitlab_issue_id=int(issue_id),
        gitlab_issue_iid=issue_iid,
        gitlab_issue_url=issue_url,
        gitlab_title=issue_title,

        huly_project_id=project_link.huly_project_id,
        huly_issue_id=str(huly_issue_id),
        huly_identifier=huly_identifier,
    )

    try:
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
    except Exception:
        db.rollback()
        raise

    return {
        "status": "synced_to_huly",
        "message": (
            "GitLab issue created in Huly "
            "and mapping saved."
        ),
        "mapping_id": mapping.id,
        "gitlab_issue_id": issue_id,
        "huly_issue_id": huly_issue_id,
        "huly_identifier": huly_identifier,
    }
