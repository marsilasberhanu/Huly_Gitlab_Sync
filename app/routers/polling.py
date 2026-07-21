from fastapi import APIRouter, HTTPException, Request, status

from app.services.huly_polling_service import HulyPollingService


router = APIRouter(
    prefix="/poll",
    tags=["Polling"],
)


@router.get("/huly")
async def poll_huly_once(request: Request):
    polling_service: HulyPollingService | None = getattr(
        request.app.state,
        "huly_polling_service",
        None,
    )

    if polling_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Huly polling service is not available.",
        )

    return await polling_service.poll_once()