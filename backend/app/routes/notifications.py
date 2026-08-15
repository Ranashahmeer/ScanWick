from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import NotificationPreference, User
from app.schemas.envelope import success_response

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

Channel = str  # "email" | "in_app" | "slack"

# Source of truth for both the event list and its default channel settings —
# previously hardcoded only in frontend/src/features/account/billing/
# notifications-tab.tsx with no backend at all. Keys/defaults mirror that
# file exactly so existing users see the same defaults they had before.
_DEFAULT_PREFERENCES: list[dict] = [
    {"event_key": "sync", "label": "Data sync complete", "email": True, "in_app": True, "slack": True},
    {"event_key": "staleData", "label": "Stale data alert", "email": True, "in_app": True, "slack": True},
    {"event_key": "stockout", "label": "Stockout alert", "email": True, "in_app": True, "slack": True},
    {"event_key": "stagnation", "label": "Stagnation alert", "email": False, "in_app": True, "slack": False},
    {"event_key": "hygiene", "label": "Hygiene Sentinel alert", "email": True, "in_app": True, "slack": False},
    {"event_key": "recommendation", "label": "AI recommendation", "email": True, "in_app": True, "slack": False},
    {"event_key": "playbook", "label": "Weekly playbook", "email": True, "in_app": True, "slack": False},
    {"event_key": "postMortem", "label": "Quarterly post-mortem", "email": False, "in_app": True, "slack": False},
    {"event_key": "teamActivity", "label": "Team activity", "email": True, "in_app": True, "slack": False},
]
_CHANNELS = ("email", "in_app", "slack")


class NotificationPreferenceIn(BaseModel):
    event_key: str
    email: bool
    in_app: bool
    slack: bool


class SavePreferencesRequest(BaseModel):
    preferences: list[NotificationPreferenceIn]


@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        (
            await db.execute(
                select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
            )
        )
        .scalars()
        .all()
    )
    overrides = {(row.event_key, row.channel): row.enabled for row in rows}

    preferences = [
        {
            "event_key": default["event_key"],
            "label": default["label"],
            "email": overrides.get((default["event_key"], "email"), default["email"]),
            "in_app": overrides.get((default["event_key"], "in_app"), default["in_app"]),
            "slack": overrides.get((default["event_key"], "slack"), default["slack"]),
        }
        for default in _DEFAULT_PREFERENCES
    ]
    return success_response(preferences)


@router.put("/preferences")
async def save_preferences(
    body: SavePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        (
            await db.execute(
                select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
            )
        )
        .scalars()
        .all()
    )
    existing_by_key = {(row.event_key, row.channel): row for row in existing}

    for preference in body.preferences:
        values = {"email": preference.email, "in_app": preference.in_app, "slack": preference.slack}
        for channel in _CHANNELS:
            enabled = values[channel]
            row = existing_by_key.get((preference.event_key, channel))
            if row is None:
                db.add(
                    NotificationPreference(
                        user_id=current_user.id,
                        event_key=preference.event_key,
                        channel=channel,
                        enabled=enabled,
                    )
                )
            elif row.enabled != enabled:
                row.enabled = enabled

    await db.commit()
    return success_response({"saved": True})
