from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AIUsageEvent(Base):
    """Normalized event table — all connectors funnel into this."""
    __tablename__ = "ai_usage_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), default="api_gateway")
    employee_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    team: Mapped[str] = mapped_column(String(100), default="")
    internal_app: Mapped[str] = mapped_column(String(200), default="")
    provider: Mapped[str] = mapped_column(String(100), default="")
    model_name: Mapped[str] = mapped_column(String(200), default="", index=True)
    task_type: Mapped[str] = mapped_column(String(100), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    request_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    expensive_model_simple_task: Mapped[bool] = mapped_column(Boolean, default=False)
