from fastapi import APIRouter, Depends
from sqlalchemy import func, text, Integer, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.browser_event import BrowserEvent
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/governance", tags=["governance"])


class ShadowAISummary(BaseModel):
    total_shadow_events: int
    unique_shadow_domains: int
    blocked_events: int
    pii_flag_events: int
    high_risk_events: int


class ShadowAIDomain(BaseModel):
    domain: str
    event_count: int
    employee_count: int
    pii_count: int
    departments: str


class GovernanceAlert(BaseModel):
    timestamp: datetime
    employee_id: str
    department: str
    domain: str
    policy_action: str
    contains_pii: bool
    pii_types: str
    risk_score: float
    shadow_ai_flag: bool


@router.get("/summary", response_model=ShadowAISummary)
def governance_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(BrowserEvent.id)).scalar() or 0
    shadow = db.query(func.count(BrowserEvent.id)).filter(BrowserEvent.shadow_ai_flag == True).scalar() or 0  # noqa
    unique_domains = (
        db.query(func.count(BrowserEvent.domain.distinct()))
        .filter(BrowserEvent.shadow_ai_flag == True)  # noqa
        .scalar() or 0
    )
    blocked = db.query(func.count(BrowserEvent.id)).filter(BrowserEvent.policy_action == "block").scalar() or 0
    pii = db.query(func.count(BrowserEvent.id)).filter(BrowserEvent.contains_pii == True).scalar() or 0  # noqa
    high_risk = db.query(func.count(BrowserEvent.id)).filter(BrowserEvent.risk_score >= 0.7).scalar() or 0

    return ShadowAISummary(
        total_shadow_events=int(shadow),
        unique_shadow_domains=int(unique_domains),
        blocked_events=int(blocked),
        pii_flag_events=int(pii),
        high_risk_events=int(high_risk),
    )


@router.get("/shadow-ai-domains", response_model=list[ShadowAIDomain])
def shadow_ai_domains(db: Session = Depends(get_db)):
    rows = (
        db.query(
            BrowserEvent.domain,
            func.count(BrowserEvent.id).label("event_count"),
            func.count(BrowserEvent.employee_id.distinct()).label("employee_count"),
            func.sum(case((BrowserEvent.contains_pii == True, 1), else_=0)).label("pii_count"),  # noqa: E712
        )
        .filter(BrowserEvent.shadow_ai_flag == True)  # noqa
        .group_by(BrowserEvent.domain)
        .order_by(text("event_count DESC"))
        .limit(20)
        .all()
    )

    out = []
    for r in rows:
        # Get departments using this domain
        dept_rows = (
            db.query(BrowserEvent.department.distinct())
            .filter(BrowserEvent.domain == r.domain, BrowserEvent.shadow_ai_flag == True)  # noqa
            .limit(3)
            .all()
        )
        depts = ", ".join(d[0] for d in dept_rows if d[0])
        out.append(ShadowAIDomain(
            domain=r.domain,
            event_count=int(r.event_count or 0),
            employee_count=int(r.employee_count or 0),
            pii_count=int(r.pii_count or 0),
            departments=depts,
        ))
    return out


@router.get("/alerts", response_model=list[GovernanceAlert])
def governance_alerts(limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(BrowserEvent)
        .filter(
            (BrowserEvent.shadow_ai_flag == True) |  # noqa
            (BrowserEvent.contains_pii == True) |    # noqa
            (BrowserEvent.policy_action.in_(["block", "warn"])) |
            (BrowserEvent.risk_score >= 0.7)
        )
        .order_by(BrowserEvent.risk_score.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        GovernanceAlert(
            timestamp=r.timestamp,
            employee_id=r.employee_id,
            department=r.department,
            domain=r.domain,
            policy_action=r.policy_action,
            contains_pii=r.contains_pii,
            pii_types=r.pii_types_detected,
            risk_score=r.risk_score,
            shadow_ai_flag=r.shadow_ai_flag,
        )
        for r in rows
    ]
