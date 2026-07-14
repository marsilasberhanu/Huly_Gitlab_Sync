from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.mapping_service import (
    list_issue_mappings,
    serialize_mapping,
)


router = APIRouter(
    prefix="/mappings",
    tags=["Mappings"],
)


@router.get("")
def list_mappings(
    db: Session = Depends(get_db),
):
    mappings = list_issue_mappings(db)

    return {
        "count": len(mappings),
        "mappings": [
            serialize_mapping(mapping)
            for mapping in mappings
        ],
    }