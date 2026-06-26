import os
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

try:
    from celery import Celery
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(REDIS_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379

    # Verify Redis is reachable
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    s.connect((host, port))
    s.close()

    celery_app = Celery(
        "tasks",
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=["app.services.video_pipeline"]
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
    CELERY_AVAILABLE = True
    logger.info("Celery initialized with broker %s", REDIS_URL)
except Exception as e:
    CELERY_AVAILABLE = False
    logger.warning(
        "Celery/Redis not reachable or not installed. Tasks will run synchronously via FastAPI BackgroundTasks: %s", e
    )

    # Stub Celery so imports succeed
    class _FakeCelery:
        def task(self, *args, **kwargs):
            """No-op decorator — just returns the function as-is."""
            def decorator(fn):
                # Attach a .delay() shim so callers can do process_video_job.delay(...)
                def _delay(*a, **kw):
                    import threading
                    t = threading.Thread(target=fn, args=a, kwargs=kw, daemon=True)
                    t.start()
                fn.delay = _delay
                return fn
            # Handle @celery_app.task used with or without arguments
            if args and callable(args[0]):
                return decorator(args[0])
            return decorator

    celery_app = _FakeCelery()
