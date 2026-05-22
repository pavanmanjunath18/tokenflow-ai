"""
Rule-based recommendation engine.
All recommendations require human review.

Deduplication: each recommendation has a signature_hash derived from
(type, department, extra_key). On regeneration:
  - If a matching hash is under investigation or accepted: keep it, update savings only.
  - If pending/rejected/resolved: replace with fresh data.
  - New signatures: create fresh records.
"""

import hashlib
import statistics
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.usage_event import AIUsageEvent
from app.models.license import AILicense
from app.models.recommendation import Recommendation
from app.models.audit_log import AuditLog
from app.models.model_pricing import ModelPricing


# ── signature helpers ─────────────────────────────────────────────────────────

def _sig(rec_type: str, *parts: str) -> str:
    """Deterministic 16-char hash for a recommendation identity."""
    key = f"{rec_type}:" + ":".join(parts)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# Statuses that should survive a regeneration pass (user is actively working on them)
_PRESERVE_STATUSES = {"investigating", "accepted"}


# ── public interface ──────────────────────────────────────────────────────────

def generate_recommendations(db: Session) -> int:
    """
    Regenerate recommendations from current data.

    Preserved: any rec with status in _PRESERVE_STATUSES — savings are updated
    but review state (notes, reviewer, status) is kept intact.

    Replaced: pending / rejected / resolved recs whose signatures reappear.

    Removed: pending recs whose signatures no longer appear in the new dataset
             (the underlying issue was resolved).
    """
    new_recs = _model_downgrade_recs(db) + _inactive_license_recs(db) + _cost_spike_recs(db)

    new_sigs = {r.signature_hash: r for r in new_recs}

    # Load existing recs by signature
    existing = {
        r.signature_hash: r
        for r in db.query(Recommendation).all()
    }

    created = 0
    updated = 0

    for sig, candidate in new_sigs.items():
        if sig in existing:
            current = existing[sig]
            if current.status in _PRESERVE_STATUSES:
                # Keep review state; only refresh projected savings and description
                current.estimated_monthly_savings = candidate.estimated_monthly_savings
                current.description = candidate.description
                current.reasoning = candidate.reasoning
                current.severity = candidate.severity
                current.updated_at = datetime.now(timezone.utc)
                updated += 1
            else:
                # Replace stale record with fresh data, reset review fields
                current.title = candidate.title
                current.description = candidate.description
                current.reasoning = candidate.reasoning
                current.estimated_monthly_savings = candidate.estimated_monthly_savings
                current.confidence_score = candidate.confidence_score
                current.severity = candidate.severity
                current.status = "pending"
                current.reviewed_by = ""
                current.reviewed_at = None
                current.review_notes = ""
                current.updated_at = datetime.now(timezone.utc)
                updated += 1
        else:
            db.add(candidate)
            created += 1

    # Drop pending recs whose signatures no longer appear (issue resolved)
    stale_pending = [
        r for sig, r in existing.items()
        if sig not in new_sigs and r.status == "pending"
    ]
    for r in stale_pending:
        db.delete(r)

    total = created + updated
    db.add(AuditLog(
        action="recommendations_generated",
        resource_type="recommendations",
        resource_id="all",
        details=f"Created {created}, updated {updated}, removed {len(stale_pending)} stale",
    ))
    db.commit()
    return total


# ── rule: expensive model for simple task ────────────────────────────────────

def _model_downgrade_recs(db: Session) -> list[Recommendation]:
    rows = (
        db.query(
            AIUsageEvent.department,
            AIUsageEvent.model_name,
            func.count(AIUsageEvent.id).label("count"),
            func.sum(AIUsageEvent.cost_usd).label("total_cost"),
        )
        .filter(AIUsageEvent.expensive_model_simple_task == True)  # noqa: E712
        .group_by(AIUsageEvent.department, AIUsageEvent.model_name)
        .order_by(text("total_cost DESC"))
        .limit(10)
        .all()
    )

    out = []
    for r in rows:
        savings = round(float(r.total_cost or 0) * 0.70, 2)
        monthly_savings = round(savings / 6, 2)
        if monthly_savings < 1:
            continue
        out.append(Recommendation(
            signature_hash=_sig("model_downgrade", r.department, r.model_name),
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
            signature_hash=_sig("inactive_license_reclaim", r.department, r.tool_name),
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
    """Flag departments with a single week that cost >2.5× their rolling average."""
    rows = (
        db.query(
            AIUsageEvent.department,
            func.date_trunc("week", AIUsageEvent.timestamp).label("week"),
            func.sum(AIUsageEvent.cost_usd).label("week_cost"),
        )
        .group_by(AIUsageEvent.department, text("week"))
        .all()
    )

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
                signature_hash=_sig("abnormal_spend_spike", dept, spike_week[:10]),
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

    return out[:5]


# ── review action ─────────────────────────────────────────────────────────────

def review_recommendation(
    rec_id: int,
    status: str,
    reviewed_by: str,
    notes: str,
    db: Session,
) -> Recommendation | None:
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        return None
    rec.status = status
    rec.reviewed_by = reviewed_by
    rec.reviewed_at = datetime.now(timezone.utc)
    rec.review_notes = notes
    if status == "resolved":
        rec.resolved_at = datetime.now(timezone.utc)
    db.add(AuditLog(
        action="recommendation_reviewed",
        resource_type="recommendation",
        resource_id=str(rec_id),
        actor=reviewed_by,
        actor_email=reviewed_by,
        details=f"Status set to {status}",
    ))
    db.commit()
    db.refresh(rec)
    return rec
