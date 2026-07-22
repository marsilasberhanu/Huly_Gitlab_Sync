import os

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.project_link import ProjectLink
from app.models.user import User
from app.schemas.project_links import (
    ProjectLinkCreate,
    ProjectLinkCreatedResponse,
    ProjectLinkResponse,
)
from app.services.project_link_service import (
    create_project_link,
    delete_project_link,
    list_project_links,
)


router = APIRouter(
    prefix="/project-links",
    tags=["Project Links"],
)


def build_webhook_url(
    request: Request,
    project_link_id: int,
) -> str:
    public_base_url = os.getenv(
        "PUBLIC_BASE_URL",
        "",
    ).strip().rstrip("/")

    if not public_base_url:
        public_base_url = str(
            request.base_url
        ).rstrip("/")

    return (
        f"{public_base_url}/webhook/gitlab/"
        f"{project_link_id}"
    )


def make_response(
    *,
    request: Request,
    link: ProjectLink,
) -> ProjectLinkResponse:
    return ProjectLinkResponse(
        id=link.id,
        gitlab_project_id=link.gitlab_project_id,
        gitlab_project_name=link.gitlab_project_name,
        huly_project_id=link.huly_project_id,
        huly_project_name=link.huly_project_name,
        is_active=link.is_active,
        webhook_url=build_webhook_url(
            request,
            link.id,
        ),
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


@router.post(
    "",
    response_model=ProjectLinkCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_link(
    data: ProjectLinkCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    link, webhook_secret = create_project_link(
        db,
        user_id=current_user.id,
        data=data,
    )

    response = make_response(
        request=request,
        link=link,
    )

    return ProjectLinkCreatedResponse(
        **response.model_dump(),
        webhook_secret=webhook_secret,
    )


@router.get(
    "",
    response_model=list[ProjectLinkResponse],
)
def get_links(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    links = list_project_links(
        db,
        user_id=current_user.id,
    )

    return [
        make_response(
            request=request,
            link=link,
        )
        for link in links
    ]


@router.delete(
    "/{project_link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_link(
    project_link_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_project_link(
        db,
        user_id=current_user.id,
        project_link_id=project_link_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
