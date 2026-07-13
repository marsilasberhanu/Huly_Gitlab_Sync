from fastapi import APIRouter, Request

from app.services.huly_to_gitlab_service import (
    sync_huly_issue_to_gitlab,
)


router = APIRouter(
    prefix="/webhook",
    tags=["Huly Webhooks"],
)


@router.post("/huly")
async def huly_webhook(request: Request):
    payload = await request.json()

    print("📩 Huly webhook/event received")
    print(payload)

    event_type = (
        payload.get("eventType")
        or payload.get("event_type")
        or "issue.created"
    )

    issue = payload.get("issue", payload)

    return await sync_huly_issue_to_gitlab(
        issue=issue,
        event_type=event_type,
        source="webhook",
    )