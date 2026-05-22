"""
Arq WorkerSettings — passed to `arq app.worker.settings.WorkerSettings`.

Configures:
  - Task functions available for execution
  - Cron: heartbeat runs every 15 min and once at startup
  - Redis connection from app config
  - Concurrency: up to 10 parallel jobs
  - Timeout: 5 min per job; 3 auto-retries on exception
  - Keep results in Redis for 10 min (for GET /api/tasks/{job_id} polling)

Start the worker:
    cd backend
    arq app.worker.settings.WorkerSettings
"""

from arq.connections import RedisSettings
from arq.cron import cron

from app.config import settings
from app.worker.tasks import sync_connector_task, heartbeat_task


class WorkerSettings:
    functions = [sync_connector_task, heartbeat_task]

    cron_jobs = [
        cron(heartbeat_task, minute={0, 15, 30, 45}, run_at_startup=True),
    ]

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    max_jobs = 10
    job_timeout = 300          # seconds; cancelled after 5 min
    max_tries = 3              # retry up to 3 times on unhandled exception
    keep_result = 600          # keep result in Redis for 10 min
    keep_result_forever = False
    health_check_interval = 30
    health_check_key = b"arq:health-check:tokenflow"
