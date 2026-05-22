from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BrowserEvent(Base):
    __tablename__ = "browser_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), default="")
    session_id: Mapped[str] = mapped_column(String(30), default="")
    browser: Mapped[str] = mapped_column(String(50), default="")
    domain: Mapped[str] = mapped_column(String(200), default="")
    task_type: Mapped[str] = mapped_column(String(100), default="")
    prompt_length_chars: Mapped[int] = mapped_column(Integer, default=0)
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    contains_pii: Mapped[bool] = mapped_column(Boolean, default=False)
    pii_types_detected: Mapped[str] = mapped_column(String(200), default="")
    policy_action: Mapped[str] = mapped_column(String(30), default="allow")
    shadow_ai_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_tool: Mapped[bool] = mapped_column(Boolean, default=True)
    copy_paste_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    file_upload_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
