from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "scanwick",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Dev convenience: `.delay()` runs the task inline instead of publishing
    # to Redis, so local testing doesn't need Redis or a separate worker
    # process running at all. Gated on dev_mode (never just the setting
    # alone) so production can never end up eager no matter how the env var
    # is set. `task_eager_propagates` makes a failure inside the task raise
    # back through `.delay()` as a real exception (matching what a broker
    # failure already does) instead of being silently swallowed into an
    # EagerResult object nobody inspects.
    task_always_eager=settings.dev_mode and settings.celery_task_always_eager,
    task_eager_propagates=settings.dev_mode and settings.celery_task_always_eager,
    # FP-D1: previously no task had any time limit at all -- one malformed
    # PDF/CSV (or a hung external API call inside a task) occupied a worker
    # permanently, and with the default prefetch multiplier that also
    # starves every other queued task behind it on that worker. Soft limit
    # raises a catchable exception inside the task first; the hard limit
    # force-kills it shortly after if that didn't work. acks_late +
    # reject_on_worker_lost means a task killed by a worker crash/OOM is
    # requeued for another worker rather than silently dropped -- safe here
    # since ingestion tasks are already idempotent (audit #14 dedup).
    # prefetch_multiplier=1 stops one worker from hoarding a batch of tasks
    # while a single one of them is stuck.
    task_soft_time_limit=300,
    task_time_limit=360,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app"])

celery_app.conf.beat_schedule = {
    # Keeps the USD->NGN checkout rate (app/services/fx_rates.py) fresh —
    # fires at the top of every hour. get_current_usd_ngn_rate() also
    # fetches on-demand if a checkout happens before the first tick (e.g.
    # right after a fresh deploy), so this is what keeps that case rare
    # rather than something checkout depends on to function at all.
    "sync-usd-ngn-rate": {
        "task": "fx.sync_usd_ngn_rate",
        "schedule": crontab(minute=0),
    },
}
