"""Worker environment settings for Redis queue consumption."""

import os


QUEUE_NAME = "automation:runs"
# The worker reads Redis and database endpoints from Docker Compose environment variables.
REDIS_URL = os.environ["REDIS_URL"]
