# Make agentgraph a package and expose celery_app for convenience
from . import tasks  # noqa: F401

# Optional: expose celery_app at package level if needed
try:
    celery_app = tasks.celery_app  # noqa: F401
except Exception:
    celery_app = None

