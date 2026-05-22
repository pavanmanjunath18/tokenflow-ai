"""
Task status API — poll arq job state by job_id.

GET /api/tasks/{job_id}
  Returns the current state of an arq job as seen in Redis.
  Useful for the frontend to poll after a sync is enqueued.

Returned status values (from arq JobStatus):
  queued       – job is in the arq queue, not yet picked up
  in_progress  – worker is currently executing the task
  complete     – finished (check result.status for success/failed)
  not_found    – job_id doesn't exist in Redis (expired or invalid)
"""

from fastapi import APIRouter

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{job_id}")
async def task_status(job_id: str):
    """Poll the status of an enqueued background job."""
    try:
        from app.services.queue_service import get_job_status
        return await get_job_status(job_id)
    except Exception as exc:
        return {
            "job_id": job_id,
            "status": "unknown",
            "error": f"Could not reach Redis: {exc}",
        }
