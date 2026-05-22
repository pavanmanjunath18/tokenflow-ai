from datetime import datetime
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    # Legacy field kept for backwards compat; prefer actor_email
    actor: Mapped[str] = mapped_column(String(200), default="system")
    actor_user_id: Mapped[str] = mapped_column(String(50), default="")
    actor_email: Mapped[str] = mapped_column(String(300), default="")
    actor_role: Mapped[str] = mapped_column(String(30), default="")
    resource_type: Mapped[str] = mapped_column(String(100), default="")
    resource_id: Mapped[str] = mapped_column(String(100), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(50), default="")
    user_agent: Mapped[str] = mapped_column(String(500), default="")
