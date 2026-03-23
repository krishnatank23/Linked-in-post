import logging
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Profile, User
from app.services.groq_client import GroqClient

logger = logging.getLogger(__name__)


class ProfileIngestionAgent:
    def __init__(self, groq: GroqClient) -> None:
        self.groq = groq

    def _extract_structured(self, raw_text: str) -> dict[str, Any]:
        system_prompt = (
            "You extract professional profile data. Return strict JSON with keys: "
            "skills (array of strings), experience (array of objects), industry (string), summary (string)."
        )
        user_prompt = f"Profile text:\n{raw_text}"

        fallback = {
            "skills": [],
            "experience": [],
            "industry": "",
            "summary": raw_text[:500],
        }
        return self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)

    def run(
        self,
        db: Session,
        user: User,
        source_type: str,
        raw_text: str,
        past_posts: list[dict[str, Any]] | None = None,
        media_metadata: list[dict[str, Any]] | None = None,
    ) -> Profile:
        extracted = self._extract_structured(raw_text)

        profile = Profile(
            user_id=user.id,
            source_type=source_type,
            raw_text=raw_text,
            skills=extracted.get("skills", []),
            experience=extracted.get("experience", []),
            industry=extracted.get("industry", ""),
            summary=extracted.get("summary", ""),
            past_posts=past_posts or [],
            media_metadata=media_metadata or [],
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info("Profile ingested for user_id=%s", user.id)
        return profile
