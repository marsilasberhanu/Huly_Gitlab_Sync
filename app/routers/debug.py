import os

from fastapi import APIRouter, Request


router = APIRouter(
    prefix="/debug",
    tags=["Debug"],
)


@router.get("/env")
async def debug_env():
    return {
        "HULY_PROJECT_ID": os.getenv("HULY_PROJECT_ID"),
        "HULY_ADAPTER_URL": os.getenv("HULY_ADAPTER_URL"),
        "HULY_POLL_INTERVAL_SECONDS": os.getenv(
            "HULY_POLL_INTERVAL_SECONDS"
        ),
        "GITLAB_DEFAULT_PROJECT_ID": os.getenv(
            "GITLAB_DEFAULT_PROJECT_ID"
        ),
        "GITLAB_PROJECT_ID": os.getenv("GITLAB_PROJECT_ID"),
        "GITLAB_BASE_URL": os.getenv("GITLAB_BASE_URL"),
        "HAS_GITLAB_API_TOKEN": bool(
            os.getenv("GITLAB_API_TOKEN")
        ),
    }


@router.get("/poller")
async def debug_poller(request: Request):
    polling_service = getattr(
        request.app.state,
        "huly_polling_service",
        None,
    )

    task = getattr(
        request.app.state,
        "huly_polling_task",
        None,
    )

    return {
        "service_exists": polling_service is not None,
        "task_exists": task is not None,
        "task_done": task.done() if task else None,
        "task_cancelled": (
            task.cancelled() if task else None
        ),
        "known_issues_count": (
            len(polling_service.known_issues)
            if polling_service
            else None
        ),
        "initialized": (
            polling_service.initialized
            if polling_service
            else None
        ),
    }