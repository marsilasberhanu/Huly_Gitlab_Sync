

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.token_encryption import decrypt_token, encrypt_token
from app.models.connected_account import ConnectedAccount
from app.schemas.connections import (
    GitLabConnectionCreate,
    HulyConnectionCreate,
)


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/")


def _upsert_account(
    db: Session,
    *,
    user_id: int,
    provider: str,
    encrypted_credential: str,
    base_url: str,
    workspace_id: str | None = None,
) -> ConnectedAccount:
    account = (
        db.query(ConnectedAccount)
        .filter(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider == provider,
        )
        .first()
    )

    if account is None:
        account = ConnectedAccount(
            user_id=user_id,
            provider=provider,
        )
        db.add(account)

    account.access_token = encrypted_credential
    account.base_url = _normalize_url(base_url)
    account.workspace_id = workspace_id
    account.is_connected = True

    try:
        db.commit()
        db.refresh(account)
        return account

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{provider.title()} account is already connected.",
        ) from exc

    except Exception:
        db.rollback()
        raise


def connect_gitlab_account(
    db: Session,
    *,
    user_id: int,
    connection_data: GitLabConnectionCreate,
) -> ConnectedAccount:
    encrypted_token = encrypt_token(connection_data.access_token)

    return _upsert_account(
        db,
        user_id=user_id,
        provider="gitlab",
        encrypted_credential=encrypted_token,
        base_url=connection_data.base_url,
    )


def connect_huly_account(
    db: Session,
    *,
    user_id: int,
    connection_data: HulyConnectionCreate,
) -> ConnectedAccount:
    encrypted_token = encrypt_token(
        connection_data.api_token
    )

    return _upsert_account(
        db,
        user_id=user_id,
        provider="huly",
        encrypted_credential=encrypted_token,
        base_url=connection_data.base_url,
        workspace_id=connection_data.workspace_id.strip(),
    )


def list_connected_accounts(
    db: Session,
    *,
    user_id: int,
) -> list[ConnectedAccount]:
    return (
        db.query(ConnectedAccount)
        .filter(ConnectedAccount.user_id == user_id)
        .order_by(ConnectedAccount.provider.asc())
        .all()
    )


def get_connected_account(
    db: Session,
    *,
    user_id: int,
    provider: str,
) -> ConnectedAccount:
    account = (
        db.query(ConnectedAccount)
        .filter(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider == provider,
            ConnectedAccount.is_connected.is_(True),
        )
        .first()
    )

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No connected {provider.title()} account was found.",
        )

    return account


def get_gitlab_credentials(
    db: Session,
    *,
    user_id: int,
) -> dict[str, str]:
    account = get_connected_account(
        db,
        user_id=user_id,
        provider="gitlab",
    )

    return {
        "access_token": decrypt_token(account.access_token),
        "base_url": account.base_url or "https://gitlab.com",
    }


def get_huly_credentials(
    db: Session,
    *,
    user_id: int,
) -> dict[str, str]:
    account = get_connected_account(
        db,
        user_id=user_id,
        provider="huly",
    )

    return {
        "token": decrypt_token(account.access_token),
        "base_url": account.base_url or "",
        "workspace": account.workspace_id or "",
    }


def disconnect_account(
    db: Session,
    *,
    user_id: int,
    provider: str,
) -> None:
    account = (
        db.query(ConnectedAccount)
        .filter(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider == provider,
        )
        .first()
    )

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No connected {provider.title()} account was found.",
        )

    try:
        db.delete(account)
        db.commit()
    except Exception:
        db.rollback()
        raise
