import os
import asyncio
from datetime import datetime, timezone
from app.clients.huly_adapter_client import HulyAdapterClient
from app.services.huly_to_gitlab_service import sync_huly_issue_to_gitlab


class HulyPollingService:
    def __init__(self):
        self.client = HulyAdapterClient()

        self.project_id = os.getenv("HULY_PROJECT_ID")
        self.interval = int(os.getenv("HULY_POLL_INTERVAL_SECONDS", "30"))

        self.last_seen_modified_on = 0
        self.known_issues: dict[str, int] = {}

        # Important:
        # First poll only records existing Huly issues.
        # It does NOT sync them again.
        self.initialized = False
        self._poll_lock = asyncio.Lock()

        print("HulyPollingService env debug:")
        print("HULY_PROJECT_ID =", self.project_id)
        print("HULY_ADAPTER_URL =", os.getenv("HULY_ADAPTER_URL"))
        print("HULY_POLL_INTERVAL_SECONDS =", self.interval)

    async def poll_once(self):
        if self._poll_lock.locked():
            return {
                "success": False,
                "status": "already_running",
                "message": "A Huly polling operation is already running.",
            }

        async with self._poll_lock:
            return await self._poll_once_unlocked()

    async def _poll_once_unlocked(self):
        if not self.project_id:
            return {
                "success": False,
                "error": "Missing HULY_PROJECT_ID inside FastAPI container",
                "env_debug": {
                    "HULY_PROJECT_ID": os.getenv("HULY_PROJECT_ID"),
                    "HULY_ADAPTER_URL": os.getenv("HULY_ADAPTER_URL"),
                    "HULY_POLL_INTERVAL_SECONDS": os.getenv("HULY_POLL_INTERVAL_SECONDS"),
                },
            }

        print("Polling Huly...")

        data = await self.client.list_issues(
            project_id=self.project_id,
            limit=100,
        )

        issues = data.get("issues", [])

        # First poll: store current state only.
        # Do not sync old issues again.
        if not self.initialized:
            for issue in issues:
                issue_id = issue["id"]
                modified_on = int(issue.get("modifiedOn") or 0)

                self.known_issues[issue_id] = modified_on

                if modified_on > self.last_seen_modified_on:
                    self.last_seen_modified_on = modified_on

            self.initialized = True

            print(f"Initial Huly snapshot loaded: {len(issues)} issue(s). No sync triggered.")

            return {
                "success": True,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "mode": "initial_snapshot",
                "message": "Initial Huly state loaded. No sync triggered.",
                "known_issues_count": len(self.known_issues),
                "changes_count": 0,
                "changes": [],
                "sync_results": [],
            }

        changes = []

        for issue in issues:
            issue_id = issue["id"]
            modified_on = int(issue.get("modifiedOn") or 0)

            previous_modified_on = self.known_issues.get(issue_id)

            if previous_modified_on is None:
                issue["eventType"] = "issue.created"

                changes.append({
                    "change_type": "created",
                    "issue": issue,
                })

            elif modified_on > previous_modified_on:
                issue["eventType"] = "issue.updated"

                changes.append({
                    "change_type": "updated",
                    "issue": issue,
                })

            self.known_issues[issue_id] = modified_on

            if modified_on > self.last_seen_modified_on:
                self.last_seen_modified_on = modified_on

        sync_results = []

        if changes:
            print(f"Detected {len(changes)} Huly change(s)")

            for change in changes:
                issue = change["issue"]

                print("📦 Raw Huly update:")
                print(issue)

                print(
                    f"[HULY {change['change_type'].upper()}] "
                    f"{issue.get('identifier')} - {issue.get('title')}"
                )

                try:
                    result = await sync_huly_issue_to_gitlab(
                        issue=issue,
                        event_type=issue.get("eventType", "issue.created"),
                        source="poller",
                    )

                    print("🔁 Poller sync result:")
                    print(result)

                    sync_results.append(result)

                except Exception as e:
                    print("❌ Huly → GitLab sync failed:")
                    print(str(e))

                    sync_results.append({
                        "status": "error",
                        "error": str(e),
                        "huly_issue_id": issue.get("id"),
                        "huly_identifier": issue.get("identifier"),
                    })

        else:
            print("No Huly changes detected")

        return {
            "success": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "mode": "normal_poll",
            "changes_count": len(changes),
            "changes": changes,
            "sync_results": sync_results,
        }

    async def start_polling(self):
        print(
            f"Starting Huly polling every {self.interval} seconds"
        )

        while True:
            try:
                await self.poll_once()
                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                print("Huly polling loop cancelled")
                raise

            except Exception as exc:
                print(f"Huly polling error: {exc}")

                await asyncio.sleep(self.interval)