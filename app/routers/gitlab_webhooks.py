import os

import httpx
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.issue_mapping import IssueMapping


router = APIRouter(
    prefix="/webhook",
    tags=["GitLab Webhooks"],
)


HULY_ADAPTER_URL = os.getenv(
    "HULY_ADAPTER_URL",
    "http://huly-adapter:3001",
)

HULY_DEFAULT_PROJECT_ID = os.getenv(
    "HULY_DEFAULT_PROJECT_ID",
    "6a44daeb397fc37bf8011aaf",
)


def find_mapping(
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


@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_event: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    payload = await request.json()

    print("📩 GitLab webhook received")
    print(f"GitLab Event Header: {x_gitlab_event}")

    if x_gitlab_event != "Issue Hook":
        return {
            "status": "ignored",
            "reason": "Not a GitLab Issue Hook",
        }

    if payload.get("object_kind") != "issue":
        return {
            "status": "ignored",
            "reason": "Not an issue event",
        }

    attributes = payload.get("object_attributes", {})
    project = payload.get("project", {})
    user = payload.get("user", {})

    gitlab_project_id = project.get("id")
    gitlab_project_name = project.get(
        "name",
        "Unknown GitLab project",
    )
    gitlab_project_url = project.get("web_url", "")

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
    issue_url = attributes.get("url", "")
    gitlab_user_name = user.get(
        "name",
        "Unknown user",
    )

    if not issue_action:
        if attributes.get("state") == "opened":
            issue_action = "open"
        elif attributes.get("state") == "closed":
            issue_action = "close"
        else:
            issue_action = "unknown"

    if not gitlab_project_id or not issue_id:
        return {
            "status": "failed",
            "reason": (
                "Missing GitLab project ID or issue ID"
            ),
        }

    print(f"--- GitLab Issue {str(issue_action).upper()} ---")
    print(f"GitLab Project ID: {gitlab_project_id}")
    print(f"GitLab Issue ID: {issue_id}")
    print(f"GitLab Issue IID: {issue_iid}")
    print(f"Title: {issue_title}")

    try:
        existing_mapping = find_mapping(
            db=db,
            gitlab_project_id=gitlab_project_id,
            gitlab_issue_id=issue_id,
        )

        if existing_mapping:
            print(
                "🟡 Mapping already exists. "
                "Not creating duplicate Huly issue."
            )

            return {
                "status": "already_synced",
                "message": (
                    "This GitLab issue is already mapped "
                    "to a Huly issue."
                ),
                "gitlab": {
                    "project_id": gitlab_project_id,
                    "issue_id": issue_id,
                    "issue_iid": issue_iid,
                    "title": issue_title,
                },
                "huly": {
                    "project_id": (
                        existing_mapping.huly_project_id
                    ),
                    "issue_id": (
                        existing_mapping.huly_issue_id
                    ),
                    "identifier": (
                        existing_mapping.huly_identifier
                    ),
                },
            }

        if issue_action not in ["open", "reopen"]:
            return {
                "status": "ignored",
                "reason": (
                    "Issue action not handled yet: "
                    f"{issue_action}"
                ),
                "message": (
                    "No mapping exists yet, and only "
                    "open/reopen creates a Huly issue."
                ),
            }

        huly_payload = {
            "projectId": HULY_DEFAULT_PROJECT_ID,
            "title": issue_title,
            "description": f"""
Created from GitLab.

GitLab Project: {gitlab_project_name}
GitLab Project URL: {gitlab_project_url}
GitLab Project ID: {gitlab_project_id}
GitLab Issue ID: {issue_id}
GitLab Issue IID: {issue_iid}
GitLab Issue URL: {issue_url}
Created/Triggered by: {gitlab_user_name}

Original GitLab Description:
{issue_description}
""",
            "issueType": "Issue",
            "priority": 2,
        }

        print("🚀 Sending issue to Huly adapter...")
        print(huly_payload)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{HULY_ADAPTER_URL}/issues",
                json=huly_payload,
            )

        if response.status_code >= 400:
            print("🔴 Huly adapter error:")
            print(response.text)

            return {
                "status": "failed_to_sync_to_huly",
                "huly_adapter_status_code": (
                    response.status_code
                ),
                "huly_adapter_response": response.text,
            }

        huly_result = response.json()

        print("✅ Huly issue created")
        print(huly_result)

        huly_issue_id = (
            huly_result.get("issueId")
            or huly_result.get("result")
        )
        huly_identifier = huly_result.get("identifier")

        if not huly_issue_id:
            return {
                "status": "failed",
                "reason": (
                    "Huly issue was created but response "
                    "did not include issueId/result."
                ),
                "huly_response": huly_result,
            }

        mapping = IssueMapping(
            gitlab_project_id=gitlab_project_id,
            gitlab_project_name=gitlab_project_name,
            gitlab_issue_id=issue_id,
            gitlab_issue_iid=issue_iid,
            gitlab_issue_url=issue_url,
            gitlab_title=issue_title,
            huly_project_id=HULY_DEFAULT_PROJECT_ID,
            huly_issue_id=huly_issue_id,
            huly_identifier=huly_identifier,
        )

        db.add(mapping)
        db.commit()
        db.refresh(mapping)

        print("✅ Mapping saved successfully")

        return {
            "status": "synced_to_huly",
            "message": (
                "GitLab issue created in Huly "
                "and mapping saved."
            ),
            "gitlab_issue_title": issue_title,
            "mapping": {
                "gitlab_project_id": gitlab_project_id,
                "gitlab_issue_id": issue_id,
                "gitlab_issue_iid": issue_iid,
                "huly_project_id": HULY_DEFAULT_PROJECT_ID,
                "huly_issue_id": huly_issue_id,
                "huly_identifier": huly_identifier,
            },
            "huly": huly_result,
        }

    except Exception as exc:
        db.rollback()

        print(
            f"🔴 Error during GitLab → Huly sync: {exc}"
        )

        return {
            "status": "error",
            "message": str(exc),
        }