from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.db.models import NotificationPreference


class NotificationSchedulerAgent:
    """Decides whether a user should receive a notification in the current dispatch cycle.

    Note: Preferred hour is interpreted in UTC for now.
    """

    def _current_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def _to_local(self, pref: NotificationPreference, now_utc: datetime | None = None) -> datetime:
        now = now_utc or self._current_utc()
        tz_name = pref.timezone or "UTC"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = timezone.utc
        return now.astimezone(tz)

    def is_preferred_hour(self, pref: NotificationPreference, now_utc: datetime | None = None) -> bool:
        local_now = self._to_local(pref, now_utc=now_utc)
        return int(local_now.hour) == int(pref.preferred_hour)

    def is_preferred_weekday(self, pref: NotificationPreference, now_utc: datetime | None = None) -> bool:
        weekdays = pref.preferred_weekdays or [0, 1, 2, 3, 4]
        local_now = self._to_local(pref, now_utc=now_utc)
        return int(local_now.weekday()) in {int(day) for day in weekdays}

    def is_due_by_cadence(self, pref: NotificationPreference, now_utc: datetime | None = None) -> bool:
        now = now_utc or self._current_utc()
        if pref.last_sent_at is None:
            return True

        last_sent = pref.last_sent_at
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)

        return now >= (last_sent + timedelta(days=int(pref.cadence_days)))

    def should_dispatch_now(self, pref: NotificationPreference, now_utc: datetime | None = None) -> tuple[bool, str]:
        if not pref.enabled:
            return False, "notifications disabled"

        if not self.is_preferred_weekday(pref, now_utc=now_utc):
            return False, "outside preferred calendar days"

        if not self.is_preferred_hour(pref, now_utc=now_utc):
            return False, "outside preferred hour window"

        if not self.is_due_by_cadence(pref, now_utc=now_utc):
            return False, "not due by cadence"

        return True, "ready"
