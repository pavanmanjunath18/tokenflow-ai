"""Core analytics queries — all read from ai_usage_events.

Filters (all optional):
  start_date  — inclusive lower bound on event timestamp (date)
  end_date    — inclusive upper bound on event timestamp (date)
  department  — exact match on department name
  provider    — exact match on provider name
  model       — exact match on model_name
"""

from dataclasses import dataclass
from datetime import datetime, date, timezone, timedelta
from sqlalchemy import func, text, case
from sqlalchemy.orm import Session

from app.models.usage_event import AIUsageEvent
from app.models.license import AILicense
from app.models.model_pricing import ModelPricing


@dataclass
class AnalyticsFilters:
    start_date: date | None = None
    end_date: date | None = None
    department: str | None = None
    provider: str | None = None
    model: str | None = None


def _base_query(db: Session, f: AnalyticsFilters):
    """Return a base AIUsageEvent query with all active filters applied."""
    q = db.query(AIUsageEvent)
    if f.start_date:
        q = q.filter(AIUsageEvent.timestamp >= datetime.combine(f.start_date, datetime.min.time()))
    if f.end_date:
        q = q.filter(AIUsageEvent.timestamp < datetime.combine(f.end_date + timedelta(days=1), datetime.min.time()))
    if f.department:
        q = q.filter(AIUsageEvent.department == f.department)
    if f.provider:
        q = q.filter(AIUsageEvent.provider == f.provider)
    if f.model:
        q = q.filter(AIUsageEvent.model_name == f.model)
    return q


# ── overview ──────────────────────────────────────────────────────────────────

def get_overview(db: Session, f: AnalyticsFilters | None = None) -> dict:
    f = f or AnalyticsFilters()
    bq = _base_query(db, f)

    q = bq.with_entities(
        func.sum(AIUsageEvent.cost_usd).label("total_spend"),
        func.sum(AIUsageEvent.total_tokens).label("total_tokens"),
        func.count(AIUsageEvent.id).label("total_requests"),
        func.min(AIUsageEvent.timestamp).label("period_start"),
        func.max(AIUsageEvent.timestamp).label("period_end"),
    ).one()

    total_spend    = float(q.total_spend or 0)
    total_tokens   = int(q.total_tokens or 0)
    total_requests = int(q.total_requests or 0)
    avg_cost       = total_spend / total_requests if total_requests else 0.0

    period_start: datetime = q.period_start or datetime.now(timezone.utc)
    period_end:   datetime = q.period_end   or datetime.now(timezone.utc)
    days = max((period_end - period_start).days, 1)
    monthly_projected = (total_spend / days) * 30

    top_dept_row = (
        bq.with_entities(AIUsageEvent.department, func.sum(AIUsageEvent.cost_usd).label("s"))
        .group_by(AIUsageEvent.department)
        .order_by(text("s DESC"))
        .first()
    )
    top_dept = top_dept_row.department if top_dept_row else "—"

    high_risk = (
        bq.with_entities(func.count(AIUsageEvent.id))
        .filter(AIUsageEvent.expensive_model_simple_task == True)  # noqa: E712
        .scalar() or 0
    )

    inactive_lic = (
        db.query(func.count(AILicense.license_id))
        .filter(AILicense.active_days_last_30 <= 3)
        .scalar() or 0
    )

    flagged_cost = float(
        bq.with_entities(func.sum(AIUsageEvent.cost_usd))
        .filter(AIUsageEvent.expensive_model_simple_task == True)  # noqa: E712
        .scalar() or 0
    )
    savings_from_downgrades = flagged_cost * 0.70

    inactive_monthly_cost = float(
        db.query(func.sum(AILicense.monthly_seat_cost))
        .filter(AILicense.active_days_last_30 <= 3)
        .scalar() or 0
    )

    return {
        "total_spend":               round(total_spend, 2),
        "monthly_projected_spend":   round(monthly_projected, 2),
        "total_tokens":              total_tokens,
        "total_requests":            total_requests,
        "avg_cost_per_request":      round(avg_cost, 6),
        "top_spending_department":   top_dept,
        "estimated_monthly_savings": round(savings_from_downgrades + inactive_monthly_cost, 2),
        "high_risk_events":          int(high_risk),
        "inactive_licenses":         int(inactive_lic),
        "period_start":              period_start.date().isoformat() if period_start else "",
        "period_end":                period_end.date().isoformat() if period_end else "",
    }


# ── spend over time ───────────────────────────────────────────────────────────

def get_spend_over_time(db: Session, f: AnalyticsFilters | None = None) -> list[dict]:
    f = f or AnalyticsFilters()
    rows = (
        _base_query(db, f)
        .with_entities(
            func.date_trunc("day", AIUsageEvent.timestamp).label("day"),
            func.sum(AIUsageEvent.cost_usd).label("cost"),
        )
        .group_by(text("day"))
        .order_by(text("day"))
        .all()
    )
    return [{"date": r.day.date().isoformat(), "cost_usd": round(float(r.cost), 4)} for r in rows]


# ── department stats ──────────────────────────────────────────────────────────

def get_department_stats(db: Session, f: AnalyticsFilters | None = None) -> list[dict]:
    f = f or AnalyticsFilters()
    expensive_simple_sum = func.sum(
        case((AIUsageEvent.expensive_model_simple_task == True, 1), else_=0)  # noqa: E712
    )

    bq = _base_query(db, f)
    rows = (
        bq.with_entities(
            AIUsageEvent.department,
            func.sum(AIUsageEvent.cost_usd).label("total_cost"),
            func.sum(AIUsageEvent.total_tokens).label("total_tokens"),
            func.count(AIUsageEvent.id).label("total_requests"),
            expensive_simple_sum.label("expensive_simple"),
        )
        .group_by(AIUsageEvent.department)
        .order_by(text("total_cost DESC"))
        .all()
    )

    # Top model per dept (respects same date/provider/model filters)
    top_models: dict[str, str] = {}
    for (dept,) in bq.with_entities(AIUsageEvent.department).distinct():
        tm = (
            bq.with_entities(AIUsageEvent.model_name, func.count(AIUsageEvent.id).label("c"))
            .filter(AIUsageEvent.department == dept)
            .group_by(AIUsageEvent.model_name)
            .order_by(text("c DESC"))
            .first()
        )
        top_models[dept] = tm.model_name if tm else "—"

    out = []
    for r in rows:
        tc = float(r.total_cost or 0)
        tr = int(r.total_requests or 0)
        out.append({
            "department":                  r.department,
            "total_cost":                  round(tc, 2),
            "total_tokens":                int(r.total_tokens or 0),
            "total_requests":              tr,
            "avg_cost_per_request":        round(tc / tr, 6) if tr else 0.0,
            "top_model":                   top_models.get(r.department, "—"),
            "expensive_simple_task_count": int(r.expensive_simple or 0),
        })
    return out


# ── model stats ───────────────────────────────────────────────────────────────

def get_model_stats(db: Session, f: AnalyticsFilters | None = None) -> list[dict]:
    f = f or AnalyticsFilters()
    expensive_simple_sum = func.sum(
        case((AIUsageEvent.expensive_model_simple_task == True, 1), else_=0)  # noqa: E712
    )

    bq = _base_query(db, f)
    rows = (
        bq.with_entities(
            AIUsageEvent.model_name,
            AIUsageEvent.provider,
            func.sum(AIUsageEvent.cost_usd).label("total_cost"),
            func.sum(AIUsageEvent.total_tokens).label("total_tokens"),
            func.count(AIUsageEvent.id).label("total_requests"),
            expensive_simple_sum.label("expensive_simple"),
        )
        .group_by(AIUsageEvent.model_name, AIUsageEvent.provider)
        .order_by(text("total_cost DESC"))
        .all()
    )

    pricing_map: dict[str, ModelPricing] = {
        p.model_name: p for p in db.query(ModelPricing).all()
    }

    out = []
    for r in rows:
        tc = float(r.total_cost or 0)
        tr = int(r.total_requests or 0)
        exp_count = int(r.expensive_simple or 0)
        pricing = pricing_map.get(r.model_name)
        tier = pricing.tier if pricing else "unknown"

        flagged_cost = 0.0
        if exp_count and pricing and pricing.tier in ("premium", "ultra"):
            avg_cost_per_req = tc / tr if tr else 0
            flagged_cost = avg_cost_per_req * exp_count * 0.75

        out.append({
            "model_name":                       r.model_name,
            "provider":                         r.provider or "Unknown",
            "tier":                             tier,
            "total_cost":                       round(tc, 2),
            "total_tokens":                     int(r.total_tokens or 0),
            "total_requests":                   tr,
            "expensive_simple_task_count":      exp_count,
            "estimated_savings_if_downgraded":  round(flagged_cost, 2),
        })
    return out


# ── filter helpers ────────────────────────────────────────────────────────────

def get_available_departments(db: Session) -> list[str]:
    rows = db.query(AIUsageEvent.department).distinct().order_by(AIUsageEvent.department).all()
    return [r.department for r in rows if r.department]


def get_available_providers(db: Session) -> list[str]:
    rows = db.query(AIUsageEvent.provider).distinct().order_by(AIUsageEvent.provider).all()
    return [r.provider for r in rows if r.provider]
