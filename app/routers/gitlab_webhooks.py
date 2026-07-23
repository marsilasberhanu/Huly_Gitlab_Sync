import json
import logging

from fastapi import (
    APIRouter,
    Depends,
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


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/webhook",
    tags=["GitLab webhooks"],
)


@router.post("/gitlab/{project_link_id}")
async def gitlab_webhook(
    project_link_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticate, map and synchronize a GitLab issue event.
    """

    logger.info(
        "GitLab webhook received: project_link_id=%s",
        project_link_id,
    )

    # 1. Find the GitLab ↔ Huly project link.
    project_link = get_project_link(
        db,
        project_link_id=project_link_id,
    )

    # 2. Authenticate GitLab using the one-time secret
    # that was configured in GitLab.
    received_secret = request.headers.get(
        "X-Gitlab-Token",
        "",
    )

    if not received_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing GitLab webhook token",
        )

    if not verify_webhook_secret(
        provided_secret=received_secret,
        expected_hash=(
            project_link.webhook_secret_hash
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitLab webhook token",
        )

    # 3. Parse the webhook payload.
    try:
        payload = await request.json()

    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body is not valid JSON",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook JSON body must be an object",
        )

    # 4. Confirm the event came from the GitLab project
    # stored in this project link.
    project_data = payload.get("project")

    payload_project_id = None

    if isinstance(project_data, dict):
        payload_project_id = project_data.get("id")

    if payload_project_id is None:
        payload_project_id = payload.get(
            "project_id"
        )

    if payload_project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitLab project ID is missing",
        )

    if str(payload_project_id) != str(
        project_link.gitlab_project_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Webhook GitLab project does not match "
                "the selected project link"
            ),
        )

    gitlab_event = request.headers.get(
        "X-Gitlab-Event"
    )

    # 5. Start the actual GitLab → Huly sync.
    result = await sync_gitlab_issue_to_huly(
        payload=payload,
        gitlab_event=gitlab_event,
        project_link=project_link,
        db=db,
    )

    logger.info(
        "GitLab webhook completed: "
        "project_link_id=%s result=%s",
        project_link.id,
        result.get("status"),
    )

    return result