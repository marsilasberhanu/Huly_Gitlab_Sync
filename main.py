from fastapi import FastAPI, Request, Header
from fastapi.responses import HTMLResponse
from pathlib import Path
import asyncio
import os
import httpx
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from app.clients.huly_client import HulyClient
from app.clients.gitlab_client import GitLabClient
from app.database import init_db, SessionLocal
from app.models.issue_mapping import IssueMapping
from app.services.huly_polling_service import HulyPollingService
from app.services.huly_to_gitlab_service import sync_huly_issue_to_gitlab
from app.routers import auth

huly_polling_service: HulyPollingService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global huly_polling_service

    print("🚀 FastAPI lifespan startup running", flush=True)
    print("HULY_PROJECT_ID =", os.getenv("HULY_PROJECT_ID"), flush=True)
    print("HULY_ADAPTER_URL =", os.getenv("HULY_ADAPTER_URL"), flush=True)
    print("HULY_POLL_INTERVAL_SECONDS =", os.getenv("HULY_POLL_INTERVAL_SECONDS"), flush=True)

    huly_polling_service = HulyPollingService()

    print("🚀 Starting background Huly polling task", flush=True)

    task = asyncio.create_task(
        huly_polling_service.start_polling()
    )

    app.state.huly_polling_task = task

    def on_task_done(t):
        try:
            t.result()
        except asyncio.CancelledError:
            print("🛑 Background Huly polling task cancelled", flush=True)
        except Exception as e:
            print("🔴 Background Huly polling task crashed:", flush=True)
            print(str(e), flush=True)

    task.add_done_callback(on_task_done)

    try:
        yield

    finally:
        print("🛑 FastAPI lifespan shutdown running", flush=True)

        task = getattr(app.state, "huly_polling_task", None)

        if task:
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                print("🛑 Background Huly polling task cancelled", flush=True)


app = FastAPI(lifespan=lifespan)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    dashboard_path = Path("app/frontend/dashboard.html")

    if not dashboard_path.exists():
        return HTMLResponse(
            content="<h1>Dashboard file not found</h1>",
            status_code=404,
        )

    return HTMLResponse(content=dashboard_path.read_text())


huly_client = HulyClient()
gitlab_client = GitLabClient()

GITLAB_DEFAULT_PROJECT_ID = os.getenv("GITLAB_DEFAULT_PROJECT_ID")

HULY_ADAPTER_URL = os.getenv("HULY_ADAPTER_URL", "http://huly-adapter:3001")

HULY_DEFAULT_PROJECT_ID = os.getenv(
    "HULY_DEFAULT_PROJECT_ID",
    "6a44daeb397fc37bf8011aaf"
)


@app.get("/")
def read_root():
    return {"message": "Hello World! Your synchronization engine is ready."}


@app.get("/mappings")
def list_mappings():
    db = SessionLocal()

    try:
        mappings = db.query(IssueMapping).order_by(IssueMapping.id.desc()).all()

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

    finally:
        db.close()


def find_mapping(db, gitlab_project_id: int, gitlab_issue_id: int):
    return (
        db.query(IssueMapping)
        .filter(
            IssueMapping.gitlab_project_id == gitlab_project_id,
            IssueMapping.gitlab_issue_id == gitlab_issue_id,
        )
        .first()
    )


def find_mapping_by_huly(db, huly_project_id: str, huly_issue_id: str):
    return (
        db.query(IssueMapping)
        .filter(
            IssueMapping.huly_project_id == huly_project_id,
            IssueMapping.huly_issue_id == huly_issue_id,
        )
        .first()
    )


@app.post("/webhook/gitlab")
async def gitlab_webhook(request: Request, x_gitlab_event: str = Header(None)):
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
    gitlab_project_name = project.get("name", "Unknown GitLab project")
    gitlab_project_url = project.get("web_url", "")

    issue_id = attributes.get("id")
    issue_iid = attributes.get("iid")
    issue_title = attributes.get("title", "Untitled GitLab issue")
    issue_description = attributes.get("description") or "No description provided."
    issue_action = attributes.get("action")
    issue_url = attributes.get("url", "")
    gitlab_user_name = user.get("name", "Unknown user")

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
            "reason": "Missing GitLab project ID or issue ID",
        }

    print(f"--- GitLab Issue {str(issue_action).upper()} ---")
    print(f"GitLab Project ID: {gitlab_project_id}")
    print(f"GitLab Issue ID: {issue_id}")
    print(f"GitLab Issue IID: {issue_iid}")
    print(f"Title: {issue_title}")

    db = SessionLocal()

    try:
        existing_mapping = find_mapping(
            db=db,
            gitlab_project_id=gitlab_project_id,
            gitlab_issue_id=issue_id,
        )

        if existing_mapping:
            print("🟡 Mapping already exists. Not creating duplicate Huly issue.")
            print(
                f"GitLab Issue {issue_id} → Huly Issue {existing_mapping.huly_issue_id}"
            )

            return {
                "status": "already_synced",
                "message": "This GitLab issue is already mapped to a Huly issue.",
                "gitlab": {
                    "project_id": gitlab_project_id,
                    "issue_id": issue_id,
                    "issue_iid": issue_iid,
                    "title": issue_title,
                },
                "huly": {
                    "project_id": existing_mapping.huly_project_id,
                    "issue_id": existing_mapping.huly_issue_id,
                    "identifier": existing_mapping.huly_identifier,
                },
            }

        if issue_action not in ["open", "reopen"]:
            return {
                "status": "ignored",
                "reason": f"Issue action not handled yet: {issue_action}",
                "message": "No mapping exists yet, and only open/reopen creates a Huly issue.",
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
                "huly_adapter_status_code": response.status_code,
                "huly_adapter_response": response.text,
            }

        huly_result = response.json()

        print("✅ Huly issue created")
        print(huly_result)

        huly_issue_id = huly_result.get("issueId") or huly_result.get("result")
        huly_identifier = huly_result.get("identifier")

        if not huly_issue_id:
            return {
                "status": "failed",
                "reason": "Huly issue was created but response did not include issueId/result.",
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
        print(f"GitLab Issue {issue_id} → Huly Issue {huly_issue_id}")

        return {
            "status": "synced_to_huly",
            "message": "GitLab issue created in Huly and mapping saved.",
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

    except Exception as e:
        db.rollback()
        print(f"🔴 Error during GitLab → Huly sync: {e}")

        return {
            "status": "error",
            "message": str(e),
        }

    finally:
        db.close()

@app.get("/poll/huly")
async def poll_huly_once():
    global huly_polling_service

    if huly_polling_service is None:
        huly_polling_service = HulyPollingService()

    return await huly_polling_service.poll_once()






# @app.on_event("startup")
# async def startup_event():
#     global huly_polling_service

#     print("🚀 FastAPI startup event running")
#     print("HULY_PROJECT_ID =", os.getenv("HULY_PROJECT_ID"))
#     print("HULY_ADAPTER_URL =", os.getenv("HULY_ADAPTER_URL"))
#     print("HULY_POLL_INTERVAL_SECONDS =", os.getenv("HULY_POLL_INTERVAL_SECONDS"))

#     huly_polling_service = HulyPollingService()

#     print("🚀 Starting background Huly polling task")

#     task = asyncio.create_task(huly_polling_service.start_polling())

#     def task_done_callback(t):
#         try:
#             t.result()
#         except Exception as e:
#             print("🔴 Background Huly polling task crashed:")
#             print(e)

#     task.add_done_callback(task_done_callback)

@app.post("/webhook/huly")
async def huly_webhook(request: Request):
    payload = await request.json()

    print("📩 Huly webhook/event received")
    print(payload)

    event_type = payload.get("eventType") or payload.get("event_type") or "issue.created"
    issue = payload.get("issue", payload)

    return await sync_huly_issue_to_gitlab(
        issue=issue,
        event_type=event_type,
        source="webhook",
    )

@app.get("/debug/env")
async def debug_env():
    return {
        "HULY_PROJECT_ID": os.getenv("HULY_PROJECT_ID"),
        "HULY_ADAPTER_URL": os.getenv("HULY_ADAPTER_URL"),
        "HULY_POLL_INTERVAL_SECONDS": os.getenv("HULY_POLL_INTERVAL_SECONDS"),
        "GITLAB_DEFAULT_PROJECT_ID": os.getenv("GITLAB_DEFAULT_PROJECT_ID"),
        "GITLAB_PROJECT_ID": os.getenv("GITLAB_PROJECT_ID"),
        "GITLAB_BASE_URL": os.getenv("GITLAB_BASE_URL"),
        "HAS_GITLAB_API_TOKEN": bool(os.getenv("GITLAB_API_TOKEN")),
    }

# --- THE HULY POLLING ENGINE ---
def normalize_huly_update(update: dict):
    event_type = update.get("eventType") or update.get("event_type") or "issue.created"

    issue = (
        update.get("issue")
        or update.get("doc")
        or update.get("object")
        or update.get("data")
        or update
    )

    return event_type, issue

@app.get("/debug/poller")
async def debug_poller():
    task = getattr(app.state, "huly_polling_task", None)

    return {
        "service_exists": huly_polling_service is not None,
        "task_exists": task is not None,
        "task_done": task.done() if task else None,
        "task_cancelled": task.cancelled() if task else None,
        "known_issues_count": len(huly_polling_service.known_issues) if huly_polling_service else None,
        "initialized": huly_polling_service.initialized if huly_polling_service else None,
    }
# async def huly_poller():
#     print("⏳ Starting Huly Poller in the background...")

#     last_sync_timestamp = datetime.now(timezone.utc).isoformat()

#     while True:
#         current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

#         try:
#             updates = await huly_client.check_for_updates(last_sync_timestamp)

#             if updates and len(updates) > 0:
#                 print(f"🟢 [{current_time}] Huly updates detected: {len(updates)}")

#                 for update in updates:
#                     print("📦 Raw Huly update:")
#                     print(update)

#                     event_type, issue = normalize_huly_update(update)

#                     result = await sync_huly_issue_to_gitlab(
#                         issue=issue,
#                         event_type=event_type,
#                         source="poller",
#                     )

#                     print("🔁 Poller sync result:")
#                     print(result)

#                 last_sync_timestamp = datetime.now(timezone.utc).isoformat()

#             else:
#                 print(f"🔄 [{current_time}] Polling Huly... No new changes.")

#         except asyncio.CancelledError:
#             print("🛑 Huly poller cancelled")
#             break

#         except Exception as e:
#             print(f"🔴 Polling Engine Error: {e}")

#         await asyncio.sleep(10)
app.include_router(auth.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)