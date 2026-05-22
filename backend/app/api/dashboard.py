from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import analytics_service
from app.schemas.common import DashboardOverview, SpendPoint, DepartmentStat, ModelStat

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def overview(db: Session = Depends(get_db)):
    return analytics_service.get_overview(db)


@router.get("/spend-over-time", response_model=list[SpendPoint])
def spend_over_time(db: Session = Depends(get_db)):
    return analytics_service.get_spend_over_time(db)


@router.get("/departments", response_model=list[DepartmentStat])
def departments(db: Session = Depends(get_db)):
    return analytics_service.get_department_stats(db)


@router.get("/models", response_model=list[ModelStat])
def models(db: Session = Depends(get_db)):
    return analytics_service.get_model_stats(db)
