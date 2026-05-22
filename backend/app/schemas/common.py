from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Integration ──────────────────────────────────────────────────────────────

class IntegrationStatus(OrmBase):
    source_name: str
    source_type: str
    connection_mode: str
    rows_ingested: int
    last_sync: datetime | None
    status: str
    schema_valid: bool
    production_equivalent: str


class SyncResponse(BaseModel):
    source: str
    rows_ingested: int
    rows_failed: int
    status: str
    message: str


# ── Dashboard ────────────────────────────────────────────────────────────────

class DashboardOverview(BaseModel):
    total_spend: float
    monthly_projected_spend: float
    total_tokens: int
    total_requests: int
    avg_cost_per_request: float
    top_spending_department: str
    estimated_monthly_savings: float
    high_risk_events: int
    inactive_licenses: int
    period_start: str
    period_end: str


class SpendPoint(BaseModel):
    date: str
    cost_usd: float


class DepartmentStat(BaseModel):
    department: str
    total_cost: float
    total_tokens: int
    total_requests: int
    avg_cost_per_request: float
    top_model: str
    expensive_simple_task_count: int


class ModelStat(BaseModel):
    model_name: str
    provider: str
    tier: str
    total_cost: float
    total_tokens: int
    total_requests: int
    expensive_simple_task_count: int
    estimated_savings_if_downgraded: float


# ── Licenses ─────────────────────────────────────────────────────────────────

class LicenseWaste(BaseModel):
    license_id: str
    employee_id: str
    department: str
    tool_name: str
    plan_type: str
    monthly_seat_cost: float
    active_days_last_30: int
    license_status: str
    waste_reason: str
    last_active_date: date | None


class LicenseWasteSummary(BaseModel):
    inactive_licenses: int
    duplicate_licenses: int
    total_monthly_waste: float
    licenses: list[LicenseWaste]


# ── Recommendations ──────────────────────────────────────────────────────────

class RecommendationOut(OrmBase):
    id: int
    created_at: datetime
    recommendation_type: str
    severity: str
    department: str
    employee_id: str
    title: str
    description: str
    reasoning: str
    estimated_monthly_savings: float
    confidence_score: float
    status: str
    requires_human_review: bool


class RecommendationReview(BaseModel):
    status: str  # accepted / rejected / investigating / resolved
    reviewed_by: str
    review_notes: str = ""


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditLogOut(OrmBase):
    id: int
    timestamp: datetime
    action: str
    actor: str
    resource_type: str
    resource_id: str
    details: str
