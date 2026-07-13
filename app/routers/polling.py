from fastapi import APIRouter, Request

from app.services.huly_polling_service import HulyPollingService


router = APIRouter(
    prefix="/poll",
    tags=["Polling"],
)


@router.get("/huly")
async def poll_huly_once(request: Request):
    polling_service = getattr(
        request.app.state,
        "huly_polling_service",
        None,
    )

    if polling_service is None:
        polling_service = HulyPollingService()
        request.app.state.huly_polling_service = polling_service

    return await polling_service.poll_once()