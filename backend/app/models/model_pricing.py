from sqlalchemy import String, Float, Date
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from app.database import Base


class ModelPricing(Base):
    __tablename__ = "model_pricing"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    tier: Mapped[str] = mapped_column(String(50), default="standard")
    input_cost_per_1m_tokens: Mapped[float] = mapped_column(Float, default=0.0)
    output_cost_per_1m_tokens: Mapped[float] = mapped_column(Float, default=0.0)
    cached_input_cost_per_1m_tokens: Mapped[float] = mapped_column(Float, default=0.0)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
