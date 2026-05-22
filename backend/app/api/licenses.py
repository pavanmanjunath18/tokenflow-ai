from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.license_service import get_license_waste
from app.schemas.common import LicenseWasteSummary

router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.get("/waste", response_model=LicenseWasteSummary)
def license_waste(db: Session = Depends(get_db)):
    return get_license_waste(db)
