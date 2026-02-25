"""Celery application factory and task configuration.

Manages distributed task orchestration for transcription, enrichment, and synthesis.
Uses Redis as both message broker and result backend.
"""

import logging
from celery import Celery
from kombu import Exchange, Queue
from .config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app
# Use full Redis URL if provided, otherwise construct from host/port
if settings.redis_url:
    # Handle db number in URL - append /0 for broker and /1 for backend
    base_url = settings.redis_url.rstrip('/')
    broker_url = f"{base_url}/0"
    backend_url = f"{base_url}/1"
else:
    broker_url = f"redis://{settings.redis_host}:{settings.redis_port}/0"
    backend_url = f"redis://{settings.redis_host}:{settings.redis_port}/1"

app = Celery(
    "linkd",
    broker=broker_url,
    backend=backend_url,
)

# Configure Celery
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Task timeouts
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit with exception
    
    # Retry settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Worker pool settings
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
)

# Define task queues with priority routing
app.conf.task_queues = (
    # CPU-intensive tasks (transcription, synthesis)
    Queue(
        "transcription",
        Exchange("transcription", type="direct"),
        routing_key="transcription",
        priority=10,
    ),
    # I/O-bound tasks (scraping, API calls)
    Queue(
        "enrichment",
        Exchange("enrichment", type="direct"),
        routing_key="enrichment",
        priority=5,
    ),
    # Default queue
    Queue(
        "default",
        Exchange("default", type="direct"),
        routing_key="default",
        priority=0,
    ),
)

# Task routing
app.conf.task_routes = {
    "src.tasks.transcription_tasks.*": {"queue": "transcription"},
    "src.tasks.enrichment_tasks.*": {"queue": "enrichment"},
    "src.tasks.synthesis_tasks.*": {"queue": "transcription"},
    "src.tasks.pii_scrubbing.*": {"queue": "default"},
}

logger.info("Celery app initialized with Redis broker")
