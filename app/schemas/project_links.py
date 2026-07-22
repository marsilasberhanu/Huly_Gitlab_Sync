from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectLinkCreate(BaseModel):
    gitlab_project_id: int = Field(gt=0)
    gitlab_project_name: str | None = Field(
        default=None,
        max_length=255,
    )

    huly_project_id: str = Field(
        min_length=1,
        max_length=255,
    )
    huly_project_name: str | None = Field(
        default=None,
        max_length=255,
    )


class ProjectLinkResponse(BaseModel):
    id: int
    gitlab_project_id: int
    gitlab_project_name: str | None
    huly_project_id: str
    huly_project_name: str | None
    is_active: bool
    webhook_url: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectLinkCreatedResponse(ProjectLinkResponse):
    # Returned only when the link is created.
    webhook_secret: str
