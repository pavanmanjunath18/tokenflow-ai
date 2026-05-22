"""Rule-based recommendation engine. All recommendations require human review."""

from datetime import datetime
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.usage_event import AIUsageEvent
from app.models.license import AILicense
from app.models.recommendation import Recommendation
from app.models.audit_log import AuditLog
from app.models.model_pricing import ModelPricing


def generate_recommendations(db: Session) -> int:
    """Clear stale pending recs and regenerate from current data."""
    db.query(Recommendation).filter(Recommendation.status == "pending").delete()

    recs: list[Recommendation] = []
    recs.extend(_model_downgrade_recs(db))
    recs.extend(_inactive_license_recs(db))
    recs.extend(_cost_spike_recs(db))

    db.add_all(recs)
    db.add(AuditLog(
        action="recommendations_generated",
        resource_type="recommendations",
        resource_id="all",
        details=f"Generated {len(recs)} recommendations",
    ))
    db.commit()
    return len(recs)


# ── rule: expensive model for simple task ────────────────────────────────────

def _model_downgrade_recs(db: Session) -> list[Recommendation]:
    rows = (
        db.query(
            AIUsageEvent.department,
            AIUsageEvent.model_name,
            func.count(AIUsageEvent.id).label("count"),
            func.sum(AIUsageEvent.cost_usd).label("total_cost"),
        )
        .filter(AIUsageEvent.expensive_model_simple_task == True)
        .group_by(AIUsageEvent.department, AIUsageEvent.model_name)
        .order_by(text("total_cost DESC"))
        .limit(10)
        .all()
    )

    out = []
    for r in rows:
        savings = round(float(r.total_cost or 0) * 0.70, 2)
        monthly_savings = round(savings / 6, 2)  # dataset spans ~6 months
        if monthly_savings < 1:
            continue
        out.append(Recommendation(
            recommendation_type="model_downgrade",
            severity="high" if monthly_savings > 50 else "medium",
            department=r.department,
            title=f"Downgrade {r.model_name} for simple tasks in {r.department}",
            description=(
                f"{r.count} requests in {r.department} used {r.model_name} "
                f"for simple tasks (email drafts, summaries, CRM notes). "
                f"A standard-tier model would deliver identical quality at 70–80% lower cost."
            ),
            reasoning=(
                f"Total cost for these requests: ${float(r.total_cost or 0):.2f} over 6 months. "
                f"Flagged because task_type is in the simple-task category while model tier is premium/ultra."
            ),
            estimated_monthly_savings=monthly_savings,
            confidence_score=0.85,
            requires_human_review=True,
        ))
    return out


# ── rule: inactive paid licenses ─────────────────────────────────────────────

def _inactive_license_recs(db: Session) -> list[Recommendation]:
    rows = (
        db.query(
            AILicense.department,
            AILicense.tool_name,
            func.count(AILicense.license_id).label("count"),
            func.sum(AILicense.monthly_seat_cost).label("monthly_waste"),
        )
        .filter(AILicense.active_days_last_30 <= 3, AILicense.monthly_seat_cost > 0)
        .group_by(AILicense.department, AILicense.tool_name)
        .having(func.sum(AILicense.monthly_seat_cost) >= 20)
        .order_by(text("monthly_waste DESC"))
        .limit(8)
        .all()
    )

    out = []
    for r in rows:
        waste = round(float(r.monthly_waste or 0), 2)
        out.append(Recommendation(
            recommendation_type="inactive_license_reclaim",
            severity="high" if waste > 100 else "medium",
            department=r.department,
            title=f"Reclaim {r.count} inactive {r.tool_name} seats in {r.department}",
            description=(
                f"{r.count} {r.tool_name} licenses in {r.department} had ≤3 active days "
                f"in the last 30 days while costing ${waste}/month."
            ),
            reasoning="Seats were assigned but show minimal usage signal from the gateway traces.",
            estimated_monthly_savings=waste,
            confidence_score=0.90,
            requires_human_review=True,
        ))
    return out


# ── rule: cost spikes by department ──────────────────────────────────────────

def _cost_spike_recs(db: Session) -> list[Recommendation]:
    """Flag departments with a single week that cost >2× their average week."""
    rows = (
        db.query(
            AIUsageEvent.department,
            func.date_trunc("week", AIUsageEvent.timestamp).label("week"),
            func.sum(AIUsageEvent.cost_usd).label("week_cost"),
        )
        .group_by(AIUsageEvent.department, text("week"))
        .all()
    )

    from collections import defaultdict
    import statistics

    dept_weeks: dict[str, list[float]] = defaultdict(list)
    dept_week_map: dict[str, dict] = defaultdict(dict)

    for r in rows:
        dept_weeks[r.department].append(float(r.week_cost or 0))
        dept_week_map[r.department][str(r.week)] = float(r.week_cost or 0)

    out = []
    for dept, costs in dept_weeks.items():
        if len(costs) < 4:
            continue
        avg = statistics.mean(costs)
        if avg < 1:
            continue
        max_week_cost = max(costs)
        if max_week_cost > avg * 2.5:
            spike_week = max(dept_week_map[dept], key=dept_week_map[dept].get)
            savings = round((max_week_cost - avg) * 0.5, 2)
            out.append(Recommendation(
                recommendation_type="abnormal_spend_spike",
                severity="high",
                department=dept,
                title=f"Cost spike detected in {dept} (week of {spike_week[:10]})",
                description=(
                    f"Weekly AI spend in {dept} reached ${max_week_cost:.2f}, "
                    f"which is {max_week_cost/avg:.1f}× the rolling average of ${avg:.2f}/week."
                ),
                reasoning="Spike exceeds 2.5× rolling weekly average. Review for batch jobs, prompt loops, or unexpected usage.",
                estimated_monthly_savings=savings,
                confidence_score=0.75,
                requires_human_review=True,
            ))

    return out[:5]  # cap to top 5 spikes


# ── review action ─────────────────────────────────────────────────────────────

def review_recommendation(rec_id: int, status: str, reviewed_by: str, notes: str, db: Session) -> Recommendation | None:
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        return None
    rec.status = status
    rec.reviewed_by = reviewed_by
    rec.reviewed_at = datetime.utcnow()
    rec.review_notes = notes
    db.add(AuditLog(
        action="recommendation_reviewed",
        resource_type="recommendation",
        resource_id=str(rec_id),
        actor=reviewed_by,
        details=f"Status set to {status}",
    ))
    db.commit()
    db.refresh(rec)
    return rec
