import os
import httpx


# =========================
# Database imports
# =========================
# Adjust ONLY these imports if your actual filenames are different.

try:
    from app.database import SessionLocal
except ModuleNotFoundError:
    from app.db.database import SessionLocal


try:
    from app.models.issue_mapping import IssueMapping
except ModuleNotFoundError:
    from app.models import IssueMapping


# =========================
# Environment
# =========================

GITLAB_API_TOKEN = os.getenv("GITLAB_API_TOKEN")
GITLAB_BASE_URL = os.getenv("GITLAB_BASE_URL", "https://gitlab.com/api/v4")

GITLAB_DEFAULT_PROJECT_ID = (
    os.getenv("GITLAB_DEFAULT_PROJECT_ID")
    or os.getenv("GITLAB_PROJECT_ID")
    or os.getenv("GITLAB_PROJECT_ID_DEFAULT")
)


def normalize_gitlab_base_url(url: str) -> str:
    url = url.rstrip("/")

    if url.endswith("/api/v4"):
        return url

    return f"{url}/api/v4"


GITLAB_BASE_URL = normalize_gitlab_base_url(GITLAB_BASE_URL)


# =========================
# Mapping helpers
# =========================

def find_mapping_by_huly(db, huly_project_id: str, huly_issue_id: str):
    return (
        db.query(IssueMapping)
        .filter(
            IssueMapping.huly_project_id == str(huly_project_id),
            IssueMapping.huly_issue_id == str(huly_issue_id),
        )
        .first()
    )


# =========================
# GitLab helpers
# =========================

async def create_gitlab_issue(project_id: int | str, title: str, description: str) -> dict:
    if not GITLAB_API_TOKEN:
        raise RuntimeError("GITLAB_API_TOKEN is not set")

    url = f"{GITLAB_BASE_URL}/projects/{project_id}/issues"

    headers = {
        "PRIVATE-TOKEN": GITLAB_API_TOKEN,
        "Content-Type": "application/json",
    }

    payload = {
        "title": title,
        "description": description,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload, headers=headers)

        if response.status_code >= 400:
            raise RuntimeError(
                f"GitLab create issue failed: "
                f"{response.status_code} {response.text}"
            )

        return response.json()


# =========================
# Main Huly → GitLab sync
# =========================

async def sync_huly_issue_to_gitlab(
    issue: dict,
    event_type: str = "issue.created",
    source: str = "unknown",
):
    print(f"🔁 Huly → GitLab sync triggered from: {source}")
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
    huly_title = issue.get("title") or "Untitled Huly issue"
    huly_description = issue.get("description") or "No description provided."
    huly_url = issue.get("url", "")

    if event_type not in ["issue.created", "create", "created"]:
        return {
            "status": "ignored",
            "reason": f"Huly event not handled yet: {event_type}",
        }

    if not GITLAB_DEFAULT_PROJECT_ID:
        return {
            "status": "failed",
            "reason": "GITLAB_DEFAULT_PROJECT_ID or GITLAB_PROJECT_ID is not set",
        }

    if not huly_project_id or not huly_issue_id:
        return {
            "status": "failed",
            "reason": "Missing Huly project ID or Huly issue ID",
            "issue": issue,
        }

    db = SessionLocal()

    try:
        existing_mapping = find_mapping_by_huly(
            db=db,
            huly_project_id=str(huly_project_id),
            huly_issue_id=str(huly_issue_id),
        )

        if existing_mapping:
            print("🟡 Huly issue is already mapped. Not creating duplicate GitLab issue.")

            return {
                "status": "already_synced",
                "message": "This Huly issue is already mapped to a GitLab issue.",
                "huly": {
                    "project_id": existing_mapping.huly_project_id,
                    "issue_id": existing_mapping.huly_issue_id,
                    "identifier": existing_mapping.huly_identifier,
                },
                "gitlab": {
                    "project_id": existing_mapping.gitlab_project_id,
                    "issue_id": existing_mapping.gitlab_issue_id,
                    "issue_iid": existing_mapping.gitlab_issue_iid,
                },
            }

        gitlab_description = f"""
Created from Huly.

Huly Project ID: {huly_project_id}
Huly Issue ID: {huly_issue_id}
Huly Identifier: {huly_identifier}
Huly URL: {huly_url}

Original Huly Description:
{huly_description}
"""

        print("🚀 Creating GitLab issue from Huly issue...")

        gitlab_result = await create_gitlab_issue(
            project_id=GITLAB_DEFAULT_PROJECT_ID,
            title=huly_title,
            description=gitlab_description,
        )

        print("✅ GitLab issue created")
        print(gitlab_result)

        gitlab_project_id = gitlab_result.get("project_id") or int(GITLAB_DEFAULT_PROJECT_ID)
        gitlab_issue_id = gitlab_result.get("id")
        gitlab_issue_iid = gitlab_result.get("iid")
        gitlab_issue_url = gitlab_result.get("web_url")

        if not gitlab_issue_id:
            return {
                "status": "failed",
                "reason": "GitLab issue was created but response did not include id.",
                "gitlab_response": gitlab_result,
            }

        mapping = IssueMapping(
            gitlab_project_id=gitlab_project_id,
            gitlab_project_name=None,
            gitlab_issue_id=gitlab_issue_id,
            gitlab_issue_iid=gitlab_issue_iid,
            gitlab_issue_url=gitlab_issue_url,
            gitlab_title=huly_title,

            huly_project_id=str(huly_project_id),
            huly_issue_id=str(huly_issue_id),
            huly_identifier=huly_identifier,
        )

        db.add(mapping)
        db.commit()
        db.refresh(mapping)

        print("✅ Huly → GitLab mapping saved")
        print(f"Huly Issue {huly_issue_id} → GitLab Issue {gitlab_issue_id}")

        return {
            "status": "synced_to_gitlab",
            "message": "Huly issue created in GitLab and mapping saved.",
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

    except Exception as e:
        db.rollback()

        print(f"🔴 Error during Huly → GitLab sync: {e}")

        return {
            "status": "error",
            "message": str(e),
        }

    finally:
        db.close()