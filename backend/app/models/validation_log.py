from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class IngestionValidationLog(Base):
    __tablename__ = "ingestion_validation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("integration_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    connector_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, default=0)
    field_name: Mapped[str] = mapped_column(String(100), default="")
    # schema / missing_value / type_error / parse_error
    error_type: Mapped[str] = mapped_column(String(50), default="")
    raw_value: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
