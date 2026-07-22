import hashlib
import hmac
import secrets

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.project_link import ProjectLink
from app.schemas.project_links import ProjectLinkCreate
from app.services.connected_account_service import (
    get_connected_account,
)


def hash_webhook_secret(secret: str) -> str:
    return hashlib.sha256(
        secret.encode("utf-8")
    ).hexdigest()


def verify_webhook_secret(
    provided_secret: str,
    expected_hash: str,
) -> bool:
    provided_hash = hash_webhook_secret(provided_secret)

    return hmac.compare_digest(
        provided_hash,
        expected_hash,
    )


def create_project_link(
    db: Session,
    *,
    user_id: int,
    data: ProjectLinkCreate,
) -> tuple[ProjectLink, str]:
    # A project link is useless unless both accounts exist.
    get_connected_account(
        db,
        user_id=user_id,
        provider="gitlab",
    )
    get_connected_account(
        db,
        user_id=user_id,
        provider="huly",
    )

    raw_secret = secrets.token_urlsafe(32)

    link = ProjectLink(
        user_id=user_id,
        gitlab_project_id=data.gitlab_project_id,
        gitlab_project_name=data.gitlab_project_name,
        huly_project_id=data.huly_project_id.strip(),
        huly_project_name=data.huly_project_name,
        webhook_secret_hash=hash_webhook_secret(
            raw_secret
        ),
        is_active=True,
    )

    db.add(link)

    try:
        db.commit()
        db.refresh(link)
        return link, raw_secret

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This GitLab and Huly project pair "
                "is already linked."
            ),
        ) from exc

    except Exception:
        db.rollback()
        raise


def list_project_links(
    db: Session,
    *,
    user_id: int,
) -> list[ProjectLink]:
    return (
        db.query(ProjectLink)
        .filter(ProjectLink.user_id == user_id)
        .order_by(ProjectLink.id.asc())
        .all()
    )


def get_project_link(
    db: Session,
    *,
    project_link_id: int,
) -> ProjectLink:
    link = (
        db.query(ProjectLink)
        .filter(
            ProjectLink.id == project_link_id,
            ProjectLink.is_active.is_(True),
        )
        .first()
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project link was not found.",
        )

    return link


def get_user_project_link(
    db: Session,
    *,
    user_id: int,
    project_link_id: int,
) -> ProjectLink:
    link = (
        db.query(ProjectLink)
        .filter(
            ProjectLink.id == project_link_id,
            ProjectLink.user_id == user_id,
        )
        .first()
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project link was not found.",
        )

    return link


def delete_project_link(
    db: Session,
    *,
    user_id: int,
    project_link_id: int,
) -> None:
    link = get_user_project_link(
        db,
        user_id=user_id,
        project_link_id=project_link_id,
    )

    try:
        db.delete(link)
        db.commit()
    except Exception:
        db.rollback()
        raise
