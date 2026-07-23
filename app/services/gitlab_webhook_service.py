# app/services/gitlab_webhook_service.py

from urllib.parse import quote

import httpx


async def create_gitlab_project_webhook(
    *,
    gitlab_base_url: str,
    access_token: str,
    gitlab_project_id: str,
    callback_url: str,
    webhook_secret: str,
) -> dict:
    encoded_project_id = quote(
        str(gitlab_project_id),
        safe="",
    )

    api_url = (
        f"{gitlab_base_url.rstrip('/')}"
        f"/api/v4/projects/{encoded_project_id}/hooks"
    )

    request_body = {
        "url": callback_url,
        "token": webhook_secret,
        "issues_events": True,
        "merge_requests_events": True,
        "push_events": False,
        "enable_ssl_verification": True,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            api_url,
            headers={
                "PRIVATE-TOKEN": access_token,
            },
            json=request_body,
        )

        response.raise_for_status()
        return response.json()