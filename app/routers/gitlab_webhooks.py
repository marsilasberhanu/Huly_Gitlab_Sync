from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.gitlab_to_huly_service import (
    sync_gitlab_issue_to_huly,
)
from app.services.project_link_service import (
    get_project_link,
    verify_webhook_secret,
)


router = APIRouter(
    prefix="/webhook",
    tags=["GitLab Webhooks"],
)


@router.post("/gitlab/{project_link_id}")
async def gitlab_webhook(
    project_link_id: int,
    request: Request,
    x_gitlab_event: str | None = Header(default=None),
    x_gitlab_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    project_link = get_project_link(
        db,
        project_link_id=project_link_id,
    )

    if not x_gitlab_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing GitLab webhook secret.",
        )

    if not verify_webhook_secret(
        x_gitlab_token,
        project_link.webhook_secret_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitLab webhook secret.",
        )

    payload = await request.json()

    return await sync_gitlab_issue_to_huly(
        payload=payload,
        gitlab_event=x_gitlab_event,
        db=db,
        project_link=project_link,
    )
