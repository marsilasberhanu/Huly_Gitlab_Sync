import os
import httpx


class HulyAdapterClient:
    def __init__(self):
        self.base_url = os.getenv("HULY_ADAPTER_URL", "http://huly-adapter:3001")

    async def list_issues(self, project_id: str, limit: int = 100) -> dict:
        url = f"{self.base_url}/issues"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                params={
                    "projectId": project_id,
                    "limit": limit,
                },
            )

            response.raise_for_status()
            return response.json()