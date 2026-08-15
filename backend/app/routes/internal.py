from celery.exceptions import TimeoutError as CeleryTimeoutError
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.dependencies import get_current_user
from app.models.auth import User
from app.tasks import ping_task

router = APIRouter(prefix="/api/internal", tags=["internal"])

_RESULT_TIMEOUT_SECONDS = 10


@router.post("/ping-task", summary="Round-trip a trivial task through Celery + Redis")
async def ping_task_endpoint(current_user: User = Depends(get_current_user)):
    # Audit #11: had no auth at all — anyone could enqueue a task and block
    # a threadpool worker for up to _RESULT_TIMEOUT_SECONDS. Requiring any
    # authenticated user is enough for what this endpoint is (a Celery/
    # Redis connectivity smoke test, not something that needs merchant-
    # scoped RBAC).
    async_result = ping_task.delay()
    try:
        result = await run_in_threadpool(async_result.get, timeout=_RESULT_TIMEOUT_SECONDS)
    except CeleryTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ping_task did not complete in time — check that the Celery worker and Redis are running",
        )
    return {"task_id": async_result.id, "result": result}
