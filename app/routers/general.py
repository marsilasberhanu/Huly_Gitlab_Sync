from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(
    tags=["General"],
)


@router.get("/")
def read_root():
    return {
        "message": "Hello World! Your synchronization engine is ready."
    }


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
)
async def dashboard():
    dashboard_path = Path("app/frontend/dashboard.html")

    if not dashboard_path.exists():
        return HTMLResponse(
            content="<h1>Dashboard file not found</h1>",
            status_code=404,
        )

    return HTMLResponse(
        content=dashboard_path.read_text()
    )