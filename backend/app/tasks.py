from app.celery_app import celery_app


@celery_app.task(name="app.tasks.ping_task")
def ping_task() -> dict:
    """Trivial task that proves the broker, worker, and result backend round-trip."""
    return {"message": "pong"}
