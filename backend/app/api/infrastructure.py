from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.kubernetes_log import KubernetesLog

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])


class InfraSummary(BaseModel):
    total_requests: int
    total_errors: int
    overall_error_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    degraded_pods: int
    total_restarts: int


class PodStat(BaseModel):
    pod_name: str
    cluster: str
    avg_request_count: float
    avg_error_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    avg_cpu_percent: float
    avg_memory_mb: float
    total_restarts: int
    latest_status: str


class LatencyPoint(BaseModel):
    date: str
    avg_latency_ms: float
    p95_latency_ms: float


@router.get("/summary", response_model=InfraSummary)
def infra_summary(db: Session = Depends(get_db)):
    q = db.query(
        func.sum(KubernetesLog.request_count).label("total_req"),
        func.sum(KubernetesLog.error_count).label("total_err"),
        func.avg(KubernetesLog.avg_latency_ms).label("avg_lat"),
        func.avg(KubernetesLog.p95_latency_ms).label("p95_lat"),
        func.sum(KubernetesLog.restart_count).label("restarts"),
    ).one()

    total_req = int(q.total_req or 0)
    total_err = int(q.total_err or 0)
    degraded = (
        db.query(func.count(KubernetesLog.pod_name.distinct()))
        .filter(KubernetesLog.status == "degraded")
        .scalar() or 0
    )

    return InfraSummary(
        total_requests=total_req,
        total_errors=total_err,
        overall_error_rate=round(total_err / total_req, 4) if total_req else 0.0,
        avg_latency_ms=round(float(q.avg_lat or 0), 1),
        p95_latency_ms=round(float(q.p95_lat or 0), 1),
        degraded_pods=int(degraded),
        total_restarts=int(q.restarts or 0),
    )


@router.get("/pods", response_model=list[PodStat])
def pod_stats(db: Session = Depends(get_db)):
    rows = (
        db.query(
            KubernetesLog.pod_name,
            KubernetesLog.cluster,
            func.avg(KubernetesLog.request_count).label("avg_req"),
            func.avg(KubernetesLog.error_rate).label("avg_err_rate"),
            func.avg(KubernetesLog.avg_latency_ms).label("avg_lat"),
            func.avg(KubernetesLog.p95_latency_ms).label("p95_lat"),
            func.avg(KubernetesLog.cpu_usage_percent).label("avg_cpu"),
            func.avg(KubernetesLog.memory_usage_mb).label("avg_mem"),
            func.sum(KubernetesLog.restart_count).label("restarts"),
        )
        .group_by(KubernetesLog.pod_name, KubernetesLog.cluster)
        .order_by(text("avg_req DESC"))
        .all()
    )

    # latest status per pod
    latest: dict[str, str] = {}
    for (pod,) in db.query(KubernetesLog.pod_name).distinct():
        row = (
            db.query(KubernetesLog.status)
            .filter(KubernetesLog.pod_name == pod)
            .order_by(KubernetesLog.timestamp.desc())
            .first()
        )
        latest[pod] = row[0] if row else "unknown"

    return [
        PodStat(
            pod_name=r.pod_name,
            cluster=r.cluster,
            avg_request_count=round(float(r.avg_req or 0), 1),
            avg_error_rate=round(float(r.avg_err_rate or 0), 4),
            avg_latency_ms=round(float(r.avg_lat or 0), 1),
            p95_latency_ms=round(float(r.p95_lat or 0), 1),
            avg_cpu_percent=round(float(r.avg_cpu or 0), 1),
            avg_memory_mb=round(float(r.avg_mem or 0), 1),
            total_restarts=int(r.restarts or 0),
            latest_status=latest.get(r.pod_name, "unknown"),
        )
        for r in rows
    ]


@router.get("/latency-over-time", response_model=list[LatencyPoint])
def latency_over_time(db: Session = Depends(get_db)):
    rows = (
        db.query(
            func.date_trunc("day", KubernetesLog.timestamp).label("day"),
            func.avg(KubernetesLog.avg_latency_ms).label("avg_lat"),
            func.avg(KubernetesLog.p95_latency_ms).label("p95_lat"),
        )
        .group_by(text("day"))
        .order_by(text("day"))
        .all()
    )
    return [
        LatencyPoint(
            date=r.day.date().isoformat(),
            avg_latency_ms=round(float(r.avg_lat or 0), 1),
            p95_latency_ms=round(float(r.p95_lat or 0), 1),
        )
        for r in rows
    ]
