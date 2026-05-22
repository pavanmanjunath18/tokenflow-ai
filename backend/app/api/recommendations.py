from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.recommendation_service import (
    generate_recommendations,
    review_recommendation,
)
from app.models.recommendation import Recommendation
from app.schemas.common import RecommendationOut, RecommendationReview

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/generate")
def generate(db: Session = Depends(get_db)):
    count = generate_recommendations(db)
    return {"generated": count, "message": f"Generated {count} recommendations"}


@router.get("", response_model=list[RecommendationOut])
def list_recommendations(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Recommendation).order_by(Recommendation.created_at.desc())
    if status:
        q = q.filter(Recommendation.status == status)
    return q.all()


@router.patch("/{rec_id}/review", response_model=RecommendationOut)
def review(rec_id: int, body: RecommendationReview, db: Session = Depends(get_db)):
    valid = {"accepted", "rejected", "investigating", "resolved"}
    if body.status not in valid:
        raise HTTPException(status_code=422, detail=f"status must be one of {valid}")
    rec = review_recommendation(rec_id, body.status, body.reviewed_by, body.review_notes, db)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec
