import uuid

from sqlalchemy import Boolean, Column, Integer, String, UniqueConstraint, Uuid

from app.models.auth import Base


class NotificationPreference(Base):
    """One row per (user, event, channel) override — backs the Notifications
    tab, which previously only flipped local React state with no save action
    at all. Absence of a row for a given (event_key, channel) means "use the
    default" (see app/routes/notifications.py's default matrix); only rows
    that diverge from default are ever written."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "event_key", "channel", name="uq_notification_pref_user_event_channel"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False, index=True)
    event_key = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False)
