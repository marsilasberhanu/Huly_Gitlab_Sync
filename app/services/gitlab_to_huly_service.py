import os

import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.issue_mapping import IssueMapping
from app.models.project_link import ProjectLink


HULY_ADAPTER_URL = os.getenv(
    "HULY_ADAPTER_URL",
    "http://huly-adapter:3001",
).rstrip("/")


async def sync_gitlab_issue_to_huly(
    *,
    payload: dict,
    gitlab_event: str | None,
    project_link: ProjectLink,
    db: Session,
) -> dict:
    """
    Synchronize one GitLab issue event to the Huly project
    selected by the ProjectLink.
    """

    print(
        "📩 GitLab sync started:",
        f"project_link_id={project_link.id}",
        f"event={gitlab_event}",
        flush=True,
    )

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

    attributes = payload.get("object_attributes")
    project = payload.get("project")
    user = payload.get("user")

    if not isinstance(attributes, dict):
        attributes = {}

    if not isinstance(project, dict):
        project = {}

    if not isinstance(user, dict):
        user = {}

    gitlab_project_id = project.get("id")
    gitlab_project_name = project.get(
        "name",
        project_link.gitlab_project_name
        or "Unknown GitLab project",
    )
    gitlab_project_url = project.get(
        "web_url",
        "",
    )

    issue_id = attributes.get("id")
    issue_iid = attributes.get("iid")

    issue_title = attributes.get(
        "title",
        "Untitled GitLab issue",
    )

    issue_description = (
        attributes.get("description")
        or "No description provided."
    )

    issue_action = attributes.get("action")
    issue_state = attributes.get("state")

    issue_url = (
        attributes.get("url")
        or attributes.get("web_url")
        or ""
    )

    gitlab_user_name = user.get(
        "name",
        "Unknown user",
    )

    if not issue_action:
        if issue_state == "opened":
            issue_action = "open"
        elif issue_state == "closed":
            issue_action = "close"
        else:
            issue_action = "unknown"

    if gitlab_project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitLab project ID is missing",
        )

    if issue_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitLab issue ID is missing",
        )

    # Defense in depth: the router checks this too.
    if str(gitlab_project_id) != str(
        project_link.gitlab_project_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "GitLab project does not match "
                "the selected project link"
            ),
        )

    print(
        "GitLab issue:",
        f"project={gitlab_project_id}",
        f"issue={issue_id}",
        f"action={issue_action}",
        f"title={issue_title}",
        flush=True,
    )

    existing_mapping = (
        db.query(IssueMapping)
        .filter(
            IssueMapping.project_link_id
            == project_link.id,
            IssueMapping.gitlab_issue_id
            == issue_id,
        )
        .first()
    )

    if existing_mapping is not None:
        print(
            "🟡 Issue already synchronized:",
            f"mapping_id={existing_mapping.id}",
            flush=True,
        )

        return {
            "status": "already_synced",
            "message": (
                "This GitLab issue is already mapped "
                "to a Huly issue."
            ),
            "project_link_id": project_link.id,
            "mapping": {
                "id": existing_mapping.id,
                "gitlab_project_id": (
                    existing_mapping.gitlab_project_id
                ),
                "gitlab_issue_id": (
                    existing_mapping.gitlab_issue_id
                ),
                "gitlab_issue_iid": (
                    existing_mapping.gitlab_issue_iid
                ),
                "huly_project_id": (
                    existing_mapping.huly_project_id
                ),
                "huly_issue_id": (
                    existing_mapping.huly_issue_id
                ),
                "huly_identifier": (
                    existing_mapping.huly_identifier
                ),
            },
        }

    # For now, only creation/reopening creates a Huly issue.
    if issue_action not in {
        "open",
        "reopen",
    }:
        return {
            "status": "ignored",
            "reason": (
                f"Issue action is not handled yet: "
                f"{issue_action}"
            ),
        }

    huly_payload = {
        # This is the important change:
        # use the Huly project selected in ProjectLink.
        "projectId": project_link.huly_project_id,
        "title": issue_title,
        "description": (
            f"Created from GitLab.\n\n"
            f"Project link ID: {project_link.id}\n"
            f"GitLab Project: {gitlab_project_name}\n"
            f"GitLab Project URL: {gitlab_project_url}\n"
            f"GitLab Project ID: {gitlab_project_id}\n"
            f"GitLab Issue ID: {issue_id}\n"
            f"GitLab Issue IID: {issue_iid}\n"
            f"GitLab Issue URL: {issue_url}\n"
            f"Triggered by: {gitlab_user_name}\n\n"
            f"Original GitLab Description:\n"
            f"{issue_description}"
        ),
        "issueType": "Issue",
        "priority": 2,
    }

    print(
        "🚀 Sending issue to Huly adapter:",
        f"project_link_id={project_link.id}",
        f"huly_project_id={project_link.huly_project_id}",
        flush=True,
    )

    try:
        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:
            response = await client.post(
                f"{HULY_ADAPTER_URL}/issues",
                json=huly_payload,
            )

        response.raise_for_status()

    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text[:1000]

        print(
            "🔴 Huly adapter rejected request:",
            exc.response.status_code,
            response_text,
            flush=True,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": (
                    "Huly adapter rejected the issue"
                ),
                "adapter_status": (
                    exc.response.status_code
                ),
                "adapter_response": response_text,
            },
        ) from exc

    except httpx.RequestError as exc:
        print(
            "🔴 Huly adapter connection failed:",
            str(exc),
            flush=True,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Could not connect to the Huly adapter"
            ),
        ) from exc

    try:
        huly_result = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Huly adapter returned invalid JSON"
            ),
        ) from exc

    print(
        "✅ Huly issue response received:",
        huly_result,
        flush=True,
    )

    huly_issue_id = huly_result.get("issueId")
    huly_identifier = huly_result.get("identifier")

    if not huly_issue_id:
        result_value = huly_result.get("result")

        if isinstance(result_value, str):
            huly_issue_id = result_value

        elif isinstance(result_value, dict):
            huly_issue_id = (
                result_value.get("issueId")
                or result_value.get("id")
                or result_value.get("_id")
            )

            if not huly_identifier:
                huly_identifier = (
                    result_value.get("identifier")
                )

    if not huly_issue_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": (
                    "Huly issue may have been created, "
                    "but no issue ID was returned"
                ),
                "huly_response": huly_result,
            },
        )

    mapping = IssueMapping(
        user_id=project_link.user_id,
        project_link_id=project_link.id,
        gitlab_project_id=gitlab_project_id,
        gitlab_project_name=gitlab_project_name,
        gitlab_issue_id=issue_id,
        gitlab_issue_iid=issue_iid,
        gitlab_issue_url=issue_url,
        gitlab_title=issue_title,
        huly_project_id=project_link.huly_project_id,
        huly_issue_id=str(huly_issue_id),
        huly_identifier=huly_identifier,
    )

    db.add(mapping)

    try:
        db.commit()
        db.refresh(mapping)

    except IntegrityError as exc:
        db.rollback()

        # This can happen when GitLab sends the same
        # event twice at almost the same time.
        existing_mapping = (
            db.query(IssueMapping)
            .filter(
                IssueMapping.project_link_id
                == project_link.id,
                IssueMapping.gitlab_issue_id
                == issue_id,
            )
            .first()
        )

        if existing_mapping is not None:
            return {
                "status": "already_synced",
                "message": (
                    "The issue mapping already exists."
                ),
                "project_link_id": project_link.id,
                "mapping_id": existing_mapping.id,
            }

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Issue mapping already exists",
        ) from exc

    except Exception:
        db.rollback()
        raise

    print(
        "✅ GitLab → Huly synchronization complete:",
        f"mapping_id={mapping.id}",
        f"project_link_id={project_link.id}",
        f"huly_issue_id={mapping.huly_issue_id}",
        flush=True,
    )

    return {
        "status": "synced_to_huly",
        "message": (
            "GitLab issue created in Huly "
            "and its mapping was saved."
        ),
        "project_link_id": project_link.id,
        "user_id": project_link.user_id,
        "mapping": {
            "id": mapping.id,
            "gitlab_project_id": (
                mapping.gitlab_project_id
            ),
            "gitlab_issue_id": (
                mapping.gitlab_issue_id
            ),
            "gitlab_issue_iid": (
                mapping.gitlab_issue_iid
            ),
            "huly_project_id": (
                mapping.huly_project_id
            ),
            "huly_issue_id": (
                mapping.huly_issue_id
            ),
            "huly_identifier": (
                mapping.huly_identifier
            ),
        },
        "huly": huly_result,
    }