from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("signature_hash", name="uq_recommendation_signature"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # Deterministic hash of (type, department, extra_key) — prevents duplicate recommendations
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recommendation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # low/medium/high/critical
    department: Mapped[str] = mapped_column(String(100), default="")
    employee_id: Mapped[str] = mapped_column(String(20), default="")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    estimated_monthly_savings: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    # Statuses: pending → investigating → accepted/rejected → resolved
    status: Mapped[str] = mapped_column(String(30), default="pending")
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    reviewed_by: Mapped[str] = mapped_column(String(200), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    investigation_notes: Mapped[str] = mapped_column(Text, default="")
