import json

from redis import Redis

from app.core.config import get_settings


QUEUE_NAME = "automation:runs"


def enqueue_run(run_id: int) -> None:
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    client.rpush(QUEUE_NAME, json.dumps({"run_id": run_id}))
