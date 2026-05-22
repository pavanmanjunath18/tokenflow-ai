from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class KafkaEvent(Base):
    """Raw Kafka telemetry events — supplemental view of api_gateway traces."""
    __tablename__ = "kafka_events"
    __table_args__ = (UniqueConstraint("trace_id", name="uq_kafka_event_trace_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(String(20), default="")
    department: Mapped[str] = mapped_column(String(100), default="")
    provider: Mapped[str] = mapped_column(String(100), default="")
    model_name: Mapped[str] = mapped_column(String(200), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_result: Mapped[str] = mapped_column(String(30), default="allowed")
