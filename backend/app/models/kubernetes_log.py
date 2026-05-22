from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class KubernetesLog(Base):
    __tablename__ = "kubernetes_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    log_id: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    cluster: Mapped[str] = mapped_column(String(100), default="")
    namespace: Mapped[str] = mapped_column(String(100), default="")
    pod_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    gateway_version: Mapped[str] = mapped_column(String(30), default="")
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    p95_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cpu_usage_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_usage_mb: Mapped[int] = mapped_column(Integer, default=0)
    restart_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="healthy")
