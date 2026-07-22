import os

import httpx


class HulyAdapterClient:
    def __init__(self):
        self.base_url = os.getenv(
            "HULY_ADAPTER_URL",
            "http://huly-adapter:3001",
        ).rstrip("/")

    @staticmethod
    def _connection_headers(
        credentials: dict[str, str],
    ) -> dict[str, str]:
        token = credentials.get("token", "")
        workspace = credentials.get("workspace", "")
        url = credentials.get("base_url", "")

        if not token or not workspace or not url:
            raise RuntimeError(
                "Incomplete Huly connected-account credentials."
            )

        return {
            "X-Huly-Token": token,
            "X-Huly-Workspace": workspace,
            "X-Huly-Url": url,
        }

    async def create_issue(
        self,
        *,
        payload: dict,
        credentials: dict[str, str],
    ) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/issues",
                json=payload,
                headers=self._connection_headers(
                    credentials
                ),
            )

        if response.status_code >= 400:
            raise RuntimeError(
                "Huly adapter create issue failed: "
                f"{response.status_code} {response.text}"
            )

        return response.json()

    async def list_issues(
        self,
        project_id: str,
        limit: int = 100,
        credentials: dict[str, str] | None = None,
    ) -> dict:
        headers = (
            self._connection_headers(credentials)
            if credentials
            else {}
        )

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/issues",
                params={
                    "projectId": project_id,
                    "limit": limit,
                },
                headers=headers,
            )

        response.raise_for_status()
        return response.json()
