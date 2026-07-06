import os
import httpx
from urllib.parse import quote


class GitLabClient:
    def __init__(self):
        self.base_url = os.getenv("GITLAB_BASE_URL", "https://gitlab.com")
        self.token = os.getenv("GITLAB_API_TOKEN")

        if not self.token:
            print("⚠️ WARNING: GITLAB_API_TOKEN is not set")

        self.headers = {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json",
        }

    async def create_issue(
        self,
        project_id: str | int,
        title: str,
        description: str,
    ) -> dict:
        encoded_project_id = quote(str(project_id), safe="")

        url = f"{self.base_url}/api/v4/projects/{encoded_project_id}/issues"

        payload = {
            "title": title,
            "description": description,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers=self.headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise Exception(
                f"GitLab create issue failed: {response.status_code} {response.text}"
            )

        return response.json()