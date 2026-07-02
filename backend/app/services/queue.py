"""Redis queue service used by the backend to schedule worker execution jobs."""

import json

from redis import Redis

from app.core.config import get_settings


QUEUE_NAME = "automation:runs"


def enqueue_run(run_id: int) -> None:
    """Push a run ID into Redis so the worker can execute it asynchronously."""
    settings = get_settings()
    # The backend only enqueues a small JSON payload; the worker loads full case data from MySQL.
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    client.rpush(QUEUE_NAME, json.dumps({"run_id": run_id}))
