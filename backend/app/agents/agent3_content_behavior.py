from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Persona, Profile
from app.services.groq_client import GroqClient


class ContentBehaviorAgent:
    def __init__(self, groq: GroqClient) -> None:
        self.groq = groq

    def run(self, db: Session, profile: Profile, persona: Persona) -> dict[str, Any]:
        posts = profile.past_posts or []

        if not posts:
            behavior = {
                "engagement_patterns": ["No historical post data provided"],
                "content_types": ["Unknown"],
                "best_post_length": "Unknown",
            }
        else:
            system_prompt = (
                "Analyze LinkedIn posts and return strict JSON with keys: "
                "engagement_patterns (array), content_types (array), best_post_length (string)."
            )
            user_prompt = f"Past posts: {posts}"
            fallback = {
                "engagement_patterns": ["Narrative posts seem strong"],
                "content_types": ["Storytelling", "Tips"],
                "best_post_length": "120-220 words",
            }
            behavior = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)

        persona.content_behavior = behavior
        db.commit()
        db.refresh(persona)
        return behavior
