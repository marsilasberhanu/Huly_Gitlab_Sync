from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Provider(str, Enum):
    gitlab = "gitlab"
    huly = "huly"


class GitLabConnectionCreate(BaseModel):
    access_token: str = Field(min_length=1)
    base_url: str = Field(
        default="https://gitlab.com",
        min_length=1,
        max_length=500,
    )


class HulyConnectionCreate(BaseModel):
    api_token: str = Field(min_length=1)
    base_url: str = Field(
        min_length=1,
        max_length=500,
    )
    workspace_id: str = Field(
        min_length=1,
        max_length=255,
    )


class ConnectedAccountResponse(BaseModel):
    id: int
    provider: str
    base_url: str | None
    workspace_id: str | None
    is_connected: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)