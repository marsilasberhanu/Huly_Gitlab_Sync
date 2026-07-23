import os

import httpx

from app.database import SessionLocal
from app.models.issue_mapping import IssueMapping
from app.models.project_link import ProjectLink
from app.services.sync_origin_service import (
    build_huly_to_gitlab_marker,
)


GITLAB_API_TOKEN = os.getenv("GITLAB_API_TOKEN")

GITLAB_BASE_URL = os.getenv(
    "GITLAB_BASE_URL",
    "https://gitlab.com/api/v4",
)

GITLAB_DEFAULT_PROJECT_ID = (
    os.getenv("GITLAB_DEFAULT_PROJECT_ID")
    or os.getenv("GITLAB_PROJECT_ID")
    or os.getenv("GITLAB_PROJECT_ID_DEFAULT")
)


def normalize_gitlab_base_url(url: str) -> str:
    normalized_url = url.rstrip("/")

    if normalized_url.endswith("/api/v4"):
        return normalized_url

    return f"{normalized_url}/api/v4"


GITLAB_BASE_URL = normalize_gitlab_base_url(
    GITLAB_BASE_URL
)


async def create_gitlab_issue(
    project_id: int | str,
    title: str,
    description: str,
) -> dict:
    if not GITLAB_API_TOKEN:
        raise RuntimeError(
            "GITLAB_API_TOKEN is not configured"
        )

    url = (
        f"{GITLAB_BASE_URL}/projects/"
        f"{project_id}/issues"
    )

    headers = {
        "PRIVATE-TOKEN": GITLAB_API_TOKEN,
        "Content-Type": "application/json",
    }

    payload = {
        "title": title,
        "description": description,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            json=payload,
            headers=headers,
        )

    if response.status_code >= 400:
        raise RuntimeError(
            "GitLab create issue failed: "
            f"{response.status_code} {response.text}"
        )

    return response.json()


async def sync_huly_issue_to_gitlab(
    issue: dict,
    event_type: str = "issue.created",
    source: str = "unknown",
) -> dict:
    print(
        f"🔁 Huly → GitLab sync triggered from: {source}"
    )
    print(f"Huly event type: {event_type}")

    huly_project_id = (
        issue.get("projectId")
        or issue.get("project_id")
        or issue.get("space")
    )

    huly_issue_id = (
        issue.get("id")
        or issue.get("issueId")
        or issue.get("_id")
    )

    huly_identifier = issue.get("identifier")

    huly_title = (
        issue.get("title")
        or "Untitled Huly issue"
    )

    huly_description = (
        issue.get("description")
        or "No description provided."
    )

    huly_url = issue.get("url", "")

    supported_events = {
        "issue.created",
        "create",
        "created",
    }

    if event_type not in supported_events:
        return {
            "status": "ignored",
            "reason": (
                "Huly event not handled yet: "
                f"{event_type}"
            ),
        }

    
    if not huly_project_id or not huly_issue_id:
        return {
            "status": "failed",
            "reason": (
                "Missing Huly project ID "
                "or Huly issue ID"
            ),
            "issue": issue,
        }

    db = SessionLocal()

    try:
        project_links = (
            db.query(ProjectLink)
            .filter(
                ProjectLink.huly_project_id
                == str(huly_project_id),
                ProjectLink.is_active.is_(True),
            )
            .all()
        )

        if not project_links:
            return {
                "status": "failed",
                "reason": (
                    "No active project link was found "
                    "for this Huly project."
                ),
                "huly_project_id": str(huly_project_id),
            }

        if len(project_links) > 1:
            return {
                "status": "failed",
                "reason": (
                    "More than one active project link uses "
                    "this Huly project. The source account or "
                    "workspace must be included to identify the "
                    "correct link."
                ),
                "huly_project_id": str(huly_project_id),
                "project_link_ids": [
                    link.id
                    for link in project_links
                ],
            }

        project_link = project_links[0]

        print(
            "Project link selected:",
            f"id={project_link.id}",
            f"huly_project={project_link.huly_project_id}",
            f"gitlab_project={project_link.gitlab_project_id}",
            flush=True,
        )

        existing_mapping = (
            db.query(IssueMapping)
            .filter(
                IssueMapping.project_link_id
                == project_link.id,
                IssueMapping.huly_issue_id
                == str(huly_issue_id),
            )
            .first()
        )

        if existing_mapping:
            print(
                "🟡 Huly issue is already mapped. "
                "Not creating a duplicate GitLab issue."
            )

            return {
                "status": "already_synced",
                "message": (
                    "This Huly issue is already mapped "
                    "to a GitLab issue."
                ),
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
                "gitlab": {
                    "project_id": (
                        existing_mapping.gitlab_project_id
                    ),
                    "issue_id": (
                        existing_mapping.gitlab_issue_id
                    ),
                    "issue_iid": (
                        existing_mapping.gitlab_issue_iid
                    ),
                },
            }

        sync_marker = build_huly_to_gitlab_marker(
    project_link_id=project_link.id,
    huly_issue_id=str(huly_issue_id),
        )

        gitlab_description = f"""
        Created from Huly.

        Project Link ID: {project_link.id}
        Huly Project ID: {huly_project_id}
        Huly Issue ID: {huly_issue_id}
        Huly Identifier: {huly_identifier}
        Huly URL: {huly_url}

        Original Huly Description:
        {huly_description}

        {sync_marker}
        """.strip()

        print(
            "🚀 Creating GitLab issue from Huly issue..."
        )

        gitlab_result = await create_gitlab_issue(
        project_id=project_link.gitlab_project_id,
        title=huly_title,
        description=gitlab_description,
        )

        print("✅ GitLab issue created")
        print(gitlab_result)

        gitlab_project_id = (
            gitlab_result.get("project_id")
            or project_link.gitlab_project_id
        )

        gitlab_issue_id = gitlab_result.get("id")
        gitlab_issue_iid = gitlab_result.get("iid")
        gitlab_issue_url = gitlab_result.get("web_url")

        if not gitlab_issue_id:
            return {
                "status": "failed",
                "reason": (
                    "GitLab issue was created but "
                    "the response did not include id."
                ),
                "gitlab_response": gitlab_result,
            }
        
        mapping = IssueMapping(
        user_id=project_link.user_id,
        project_link_id=project_link.id,

        gitlab_project_id=gitlab_project_id,
        gitlab_project_name=(
            project_link.gitlab_project_name
        ),
        gitlab_issue_id=gitlab_issue_id,
        gitlab_issue_iid=gitlab_issue_iid,
        gitlab_issue_url=gitlab_issue_url,
        gitlab_title=huly_title,

        huly_project_id=project_link.huly_project_id,
        huly_issue_id=str(huly_issue_id),
        huly_identifier=huly_identifier,
        )

        db.add(mapping)
        db.commit()
        db.refresh(mapping)

        print("✅ Huly → GitLab mapping saved")
        print(
            f"Huly Issue {huly_issue_id} "
            f"→ GitLab Issue {gitlab_issue_id}"
        )

        return {
            "status": "synced_to_gitlab",
            "message": (
                "Huly issue created in GitLab "
                "and mapping saved."
            ),
            "mapping": {
                "huly_project_id": huly_project_id,
                "huly_issue_id": huly_issue_id,
                "huly_identifier": huly_identifier,
                "gitlab_project_id": gitlab_project_id,
                "gitlab_issue_id": gitlab_issue_id,
                "gitlab_issue_iid": gitlab_issue_iid,
            },
            "gitlab": gitlab_result,
        }

    except Exception as exc:
        db.rollback()

        print(
            f"🔴 Error during Huly → GitLab sync: {exc}"
        )

        return {
            "status": "error",
            "message": str(exc),
        }

    finally:
        db.close()