from datetime import date
from sqlalchemy import String, Float, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ClickHouseAggregate(Base):
    """Pre-aggregated daily analytics rows — supplemental to api_gateway traces."""
    __tablename__ = "clickhouse_aggregates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agg_id: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    employee_id: Mapped[str] = mapped_column(String(20), default="")
    department: Mapped[str] = mapped_column(String(100), default="")
    provider: Mapped[str] = mapped_column(String(100), default="")
    model_name: Mapped[str] = mapped_column(String(200), default="")
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit_count: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit_rate: Mapped[float] = mapped_column(Float, default=0.0)
