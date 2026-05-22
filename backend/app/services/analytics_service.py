"""Core analytics queries — all read from ai_usage_events."""

from datetime import datetime
from sqlalchemy import func, text, Integer, case
from sqlalchemy.orm import Session

from app.models.usage_event import AIUsageEvent
from app.models.license import AILicense
from app.models.model_pricing import ModelPricing


# ── overview ──────────────────────────────────────────────────────────────────

def get_overview(db: Session) -> dict:
    q = db.query(
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

    period_start: datetime = q.period_start or datetime.utcnow()
    period_end:   datetime = q.period_end   or datetime.utcnow()
    days = max((period_end - period_start).days, 1)
    monthly_projected = (total_spend / days) * 30

    top_dept_row = (
        db.query(AIUsageEvent.department, func.sum(AIUsageEvent.cost_usd).label("s"))
        .group_by(AIUsageEvent.department)
        .order_by(text("s DESC"))
        .first()
    )
    top_dept = top_dept_row.department if top_dept_row else "—"

    high_risk = (
        db.query(func.count(AIUsageEvent.id))
        .filter(AIUsageEvent.expensive_model_simple_task == True)  # noqa: E712
        .scalar() or 0
    )

    inactive_lic = (
        db.query(func.count(AILicense.license_id))
        .filter(AILicense.active_days_last_30 <= 3)
        .scalar() or 0
    )

    flagged_cost = float(
        db.query(func.sum(AIUsageEvent.cost_usd))
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

def get_spend_over_time(db: Session) -> list[dict]:
    rows = (
        db.query(
            func.date_trunc("day", AIUsageEvent.timestamp).label("day"),
            func.sum(AIUsageEvent.cost_usd).label("cost"),
        )
        .group_by(text("day"))
        .order_by(text("day"))
        .all()
    )
    return [{"date": r.day.date().isoformat(), "cost_usd": round(float(r.cost), 4)} for r in rows]


# ── department stats ──────────────────────────────────────────────────────────

def get_department_stats(db: Session) -> list[dict]:
    expensive_simple_sum = func.sum(
        case((AIUsageEvent.expensive_model_simple_task == True, 1), else_=0)  # noqa: E712
    )

    rows = (
        db.query(
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

    # top model per dept
    top_models: dict[str, str] = {}
    for (dept,) in db.query(AIUsageEvent.department).distinct():
        tm = (
            db.query(AIUsageEvent.model_name, func.count(AIUsageEvent.id).label("c"))
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

def get_model_stats(db: Session) -> list[dict]:
    expensive_simple_sum = func.sum(
        case((AIUsageEvent.expensive_model_simple_task == True, 1), else_=0)  # noqa: E712
    )

    rows = (
        db.query(
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
