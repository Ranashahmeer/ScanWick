import pytest

pytest_plugins = ("celery.contrib.pytest",)


@pytest.fixture()
def celery_app():
    """Use the real app Celery instance (not a throwaway test app).

    The FastAPI endpoint enqueues tasks on app.celery_app.celery_app, so the
    worker started by the celery_worker fixture must be bound to that same
    instance to actually exercise the broker + worker + result backend.
    """
    from app.celery_app import celery_app as app

    yield app


@pytest.fixture()
def celery_worker_parameters():
    # Skip celery's built-in 'celery.ping' sanity check — it isn't registered
    # in this minimal setup and is unrelated to our own ping_task.
    return {"perform_ping_check": False}
