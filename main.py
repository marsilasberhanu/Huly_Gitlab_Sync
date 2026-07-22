import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import (
    auth,
    connections,
    debug,
    general,
    gitlab_webhooks,
    huly_webhooks,
    mappings,
    polling,
)

from app.services.huly_polling_service import HulyPollingService
from app.services.huly_to_gitlab_service import sync_huly_issue_to_gitlab
from app.routers import auth


APP_ENV = os.getenv(
    "APP_ENV",
    "development",
).lower()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 FastAPI lifespan startup running", flush=True)
    print(
        "HULY_PROJECT_ID =",
        os.getenv("HULY_PROJECT_ID"),
        flush=True,
    )
    print(
        "HULY_ADAPTER_URL =",
        os.getenv("HULY_ADAPTER_URL"),
        flush=True,
    )
    print(
        "HULY_POLL_INTERVAL_SECONDS =",
        os.getenv("HULY_POLL_INTERVAL_SECONDS"),
        flush=True,
    )

    polling_service = HulyPollingService()

    app.state.huly_polling_service = polling_service

    print(
        "🚀 Starting background Huly polling task",
        flush=True,
    )

    polling_task = asyncio.create_task(
        polling_service.start_polling()
    )

    app.state.huly_polling_task = polling_task

    def on_task_done(task: asyncio.Task):
        try:
            task.result()

        except asyncio.CancelledError:
            print(
                "🛑 Background Huly polling task cancelled",
                flush=True,
            )

        except Exception as exc:
            print(
                "🔴 Background Huly polling task crashed:",
                flush=True,
            )
            print(str(exc), flush=True)

    polling_task.add_done_callback(on_task_done)

    try:
        yield

    finally:
        print(
            "🛑 FastAPI lifespan shutdown running",
            flush=True,
        )

        task = getattr(
            app.state,
            "huly_polling_task",
            None,
        )

        if task and not task.done():
            task.cancel()

            try:
                await task

            except asyncio.CancelledError:
                print(
                    "🛑 Background Huly polling task cancelled",
                    flush=True,
                )


app = FastAPI(
    title="Huly GitLab Sync Engine",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(connections.router)
app.include_router(general.router)
app.include_router(mappings.router)
app.include_router(polling.router)
app.include_router(huly_webhooks.router)
app.include_router(gitlab_webhooks.router)
if APP_ENV != "production":
    app.include_router(debug.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3000,
        reload=True,
    )