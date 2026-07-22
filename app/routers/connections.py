from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.connections import (
    ConnectedAccountResponse,
    GitLabConnectionCreate,
    HulyConnectionCreate,
    Provider,
)
from app.services.connected_account_service import (
    connect_gitlab_account,
    connect_huly_account,
    disconnect_account,
    list_connected_accounts,
)


router = APIRouter(
    prefix="/connections",
    tags=["Connected Accounts"],
)


@router.get(
    "",
    response_model=list[ConnectedAccountResponse],
)
def get_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_connected_accounts(
        db,
        user_id=current_user.id,
    )


@router.post(
    "/gitlab",
    response_model=ConnectedAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def connect_gitlab(
    connection_data: GitLabConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return connect_gitlab_account(
        db,
        user_id=current_user.id,
        connection_data=connection_data,
    )


@router.post(
    "/huly",
    response_model=ConnectedAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def connect_huly(
    connection_data: HulyConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return connect_huly_account(
        db,
        user_id=current_user.id,
        connection_data=connection_data,
    )


@router.delete(
    "/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def disconnect(
    provider: Provider,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    disconnect_account(
        db,
        user_id=current_user.id,
        provider=provider.value,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
