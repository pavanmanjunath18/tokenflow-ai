import hashlib
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import analytics_service
from app.services.analytics_service import AnalyticsFilters
from app.services import cache_service
from app.schemas.common import DashboardOverview, SpendPoint, DepartmentStat, ModelStat

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _filters(
    start_date: date | None = Query(None, description="Inclusive start date (YYYY-MM-DD)"),
    end_date:   date | None = Query(None, description="Inclusive end date (YYYY-MM-DD)"),
    department: str | None = Query(None, description="Filter by department name"),
    provider:   str | None = Query(None, description="Filter by provider (anthropic, openai, …)"),
    model:      str | None = Query(None, description="Filter by model name"),
) -> AnalyticsFilters:
    return AnalyticsFilters(
        start_date=start_date,
        end_date=end_date,
        department=department,
        provider=provider,
        model=model,
    )


def _filter_hash(f: AnalyticsFilters) -> str:
    key = f"{f.start_date}:{f.end_date}:{f.department}:{f.provider}:{f.model}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


@router.get("/overview", response_model=DashboardOverview)
def overview(
    f: AnalyticsFilters = Depends(_filters),
    db: Session = Depends(get_db),
):
    cache_key = f"dashboard:overview:{_filter_hash(f)}"
    cached = cache_service.cache_get(cache_key)
    if cached:
        return cached
    result = analytics_service.get_overview(db, f)
    cache_service.cache_set(cache_key, result if isinstance(result, dict) else result.__dict__, ttl=60)
    return result


@router.get("/spend-over-time", response_model=list[SpendPoint])
def spend_over_time(
    f: AnalyticsFilters = Depends(_filters),
    db: Session = Depends(get_db),
):
    return analytics_service.get_spend_over_time(db, f)


@router.get("/departments", response_model=list[DepartmentStat])
def departments(
    f: AnalyticsFilters = Depends(_filters),
    db: Session = Depends(get_db),
):
    return analytics_service.get_department_stats(db, f)


@router.get("/models", response_model=list[ModelStat])
def models(
    f: AnalyticsFilters = Depends(_filters),
    db: Session = Depends(get_db),
):
    return analytics_service.get_model_stats(db, f)


@router.get("/filter-options")
def filter_options(db: Session = Depends(get_db)):
    """Available filter values for the dashboard UI dropdowns. Cached for 5 min."""
    cached = cache_service.cache_get("dashboard:filter-options")
    if cached:
        return cached
    result = {
        "departments": analytics_service.get_available_departments(db),
        "providers":   analytics_service.get_available_providers(db),
    }
    cache_service.cache_set("dashboard:filter-options", result, ttl=300)
    return result
