"""Worker environment settings for Redis queue consumption."""

import os


QUEUE_NAME = "automation:runs"
# The worker reads Redis and database endpoints from Docker Compose environment variables.
REDIS_URL = os.environ["REDIS_URL"]
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
SCHEDULER_POLL_SECONDS = int(os.getenv("SCHEDULER_POLL_SECONDS", "30"))
