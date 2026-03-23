from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import GapAnalysis, GeneratedContent, NotificationPreference


class NotificationManagerAgent:
    def benchmark_cadence_days(self, db: Session, user_id: int) -> int:
        rows = db.query(GapAnalysis).filter(GapAnalysis.user_id == user_id).all()
        for row in rows:
            category = (row.category or "").lower()
            gap_text = (row.gap or "").lower()
            recommendation = (row.recommendation or "").lower()
            if "consisten" in category or "consisten" in gap_text or "cadence" in recommendation:
                return 2
        return 3

    def pick_notification_topic(self, db: Session, user_id: int, fallback_topic: str) -> str:
        strategy = (
            db.query(GeneratedContent)
            .filter(GeneratedContent.user_id == user_id, GeneratedContent.content_type == "strategy")
            .order_by(GeneratedContent.created_at.desc())
            .first()
        )
        if not strategy or not isinstance(strategy.payload, dict):
            return fallback_topic

        ideas = strategy.payload.get("post_ideas", [])
        if isinstance(ideas, list) and ideas:
            return str(ideas[0])
        return fallback_topic

    def is_due(self, pref: NotificationPreference, force_send: bool) -> tuple[bool, datetime | None]:
        if force_send or pref.last_sent_at is None:
            return True, None

        next_due = pref.last_sent_at + timedelta(days=pref.cadence_days)
        if datetime.utcnow() >= next_due:
            return True, next_due
        return False, next_due

    def build_ready_post_email(self, user_name: str, topic: str, post_payload: dict[str, Any], cadence_days: int) -> str:
        hashtags = post_payload.get("hashtags", [])
        hashtag_line = " ".join(str(tag) for tag in hashtags) if isinstance(hashtags, list) else ""
        return (
            f"Hi {user_name},\n\n"
            "Your LinkedIn benchmark reminder is ready.\n"
            f"Recommended posting cadence: every {cadence_days} day(s).\n\n"
            f"Topic: {topic}\n\n"
            "Ready-to-post content:\n\n"
            f"{post_payload.get('hook', '')}\n\n"
            f"{post_payload.get('body', '')}\n\n"
            f"{post_payload.get('cta', '')}\n"
            f"{hashtag_line}\n\n"
            "This draft is humanized and benchmark-aligned."
        )

    def mark_sent(self, db: Session, pref: NotificationPreference) -> None:
        pref.last_sent_at = datetime.utcnow()
        db.commit()
