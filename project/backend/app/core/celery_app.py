"""
PPT Master Web Service - Celery Configuration.

Configures Celery with Redis as broker and backend.
Defines task routing and retry policies for pipeline steps.
"""

import os
from typing import Any

from celery import Celery
from kombu import Exchange, Queue

# ────────────────────────────────
# Configuration
# ────────────────────────────────

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ────────────────────────────────
# Celery Instance
# ────────────────────────────────

celery_app = Celery(
    "ppt_master",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.services.pipeline_service"],
)

# ────────────────────────────────
# Queues & Routing
# ────────────────────────────────

celery_app.conf.task_queues = (
    Queue("default", Exchange("default"), routing_key="task.#"),
    Queue("llm_tasks", Exchange("llm"), routing_key="llm.#"),
    Queue("script_tasks", Exchange("scripts"), routing_key="scripts.#"),
    Queue("file_tasks", Exchange("files"), routing_key="files.#"),
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "task.default"

celery_app.conf.task_routes = {
    "app.services.pipeline.strategist_phase": {"queue": "llm_tasks", "routing_key": "llm.strategist"},
    "app.services.pipeline.executor_phase": {"queue": "llm_tasks", "routing_key": "llm.executor"},
    "app.services.pipeline.image_acquisition": {"queue": "llm_tasks", "routing_key": "llm.images"},
    "app.services.pipeline.process_source_file": {"queue": "script_tasks", "routing_key": "scripts.convert"},
    "app.services.pipeline.export_pptx": {"queue": "script_tasks", "routing_key": "scripts.export"},
    "app.services.pipeline.quality_check": {"queue": "script_tasks", "routing_key": "scripts.quality"},
    "app.services.pipeline.generate_images": {"queue": "file_tasks", "routing_key": "files.images"},
}

# ────────────────────────────────
# Task Execution Settings
# ────────────────────────────────

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task results
    result_expires=3600 * 24 * 7,  # 7 days
    result_extended=True,
    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 min soft limit
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    # Ack late for long-running tasks
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result backend
    result_backend=REDIS_URL,
)

# ────────────────────────────────
# Retry Configuration
# ────────────────────────────────

TASK_RETRY_CONFIG: dict[str, Any] = {
    "max_retries": 3,
    "default_retry_delay": 60,  # 1 minute
    "retry_backoff": True,
    "retry_backoff_max": 600,  # 10 minutes max
    "retry_jitter": True,
}

# ────────────────────────────────
# Celery Beat Schedule
# ────────────────────────────────

celery_app.conf.beat_schedule = {
    "cleanup-old-jobs": {
        "task": "app.services.pipeline.cleanup_old_jobs",
        "schedule": 3600 * 24,  # Daily
        "args": (30,),  # Keep 30 days
    },
}


# ────────────────────────────────
# Auto-Discover Tasks
# ────────────────────────────────

# Tasks will be auto-discovered from the include modules
celery_app.autodiscover_tasks()
