import os
import httpx


class HulyClient:
    def __init__(self):
        # Use the working Docker service, not the old direct Huly API
        self.adapter_url = os.getenv("HULY_ADAPTER_URL", "http://huly-adapter:3001")
        self.project_id = os.getenv(
            "HULY_DEFAULT_PROJECT_ID",
            "6a44daeb397fc37bf8011aaf"
        )

    async def check_for_updates(self, last_sync_timestamp: str):
        """
        Polls Huly through the huly-adapter.

        This expects the huly-adapter to expose a GET endpoint later:
        GET /issues?projectId=...&updatedAfter=...
        """

        url = f"{self.adapter_url}/issues"

        params = {
            "projectId": self.project_id,
            "updatedAfter": last_sync_timestamp,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)

            if response.status_code == 404:
                print("🟡 Huly adapter does not have GET /issues yet.")
                print("🟡 Poller is running, but adapter needs a list/poll endpoint.")
                return []

            if response.status_code >= 400:
                print(f"🔴 Huly adapter polling error: {response.status_code}")
                print(response.text)
                return []

            data = response.json()

            if isinstance(data, list):
                return data

            if isinstance(data, dict):
                return data.get("issues") or data.get("updates") or []

            return []

        except Exception as e:
            print(f"🔴 Huly adapter polling connection error: {e}")
            return []