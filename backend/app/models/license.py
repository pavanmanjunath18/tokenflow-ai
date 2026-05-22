from datetime import date
from sqlalchemy import String, Float, Integer, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AILicense(Base):
    __tablename__ = "ai_licenses"

    license_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(20), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(100), default="")
    monthly_seat_cost: Mapped[float] = mapped_column(Float, default=0.0)
    assigned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active_days_last_30: Mapped[int] = mapped_column(Integer, default=0)
    license_status: Mapped[str] = mapped_column(String(30), default="active")
    department: Mapped[str] = mapped_column(String(100), default="")
