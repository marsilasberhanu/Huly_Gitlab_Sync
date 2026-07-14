from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.gitlab_to_huly_service import (
    sync_gitlab_issue_to_huly,
)


router = APIRouter(
    prefix="/webhook",
    tags=["GitLab Webhooks"],
)


@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_event: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    payload = await request.json()

    return await sync_gitlab_issue_to_huly(
        payload=payload,
        gitlab_event=x_gitlab_event,
        db=db,
    )