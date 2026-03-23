from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Persona, Profile, User
from app.services.groq_client import GroqClient


class UserPersonaAgent:
    def __init__(self, groq: GroqClient) -> None:
        self.groq = groq

    def _analyze_content_behavior(self, profile: Profile) -> dict[str, Any]:
        posts = profile.past_posts or []
        if not posts:
            return {
                "engagement_patterns": ["No historical post data provided"],
                "content_types": ["Unknown"],
                "best_post_length": "Unknown",
            }

        system_prompt = (
            "Analyze LinkedIn post behavior and return strict JSON with keys: "
            "engagement_patterns (array), content_types (array), best_post_length (string)."
        )
        user_prompt = f"Past LinkedIn posts: {posts}"
        fallback = {
            "engagement_patterns": ["Narrative posts seem strong"],
            "content_types": ["Storytelling", "Tips"],
            "best_post_length": "120-220 words",
        }
        behavior = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)
        if not isinstance(behavior, dict):
            return fallback
        return behavior

    def run(self, db: Session, user: User, profile: Profile) -> Persona:
        behavior = self._analyze_content_behavior(profile)

        system_prompt = (
            "You are a LinkedIn brand strategist. Return strict JSON: "
            '{"tone":"", "style":"", "expertise":[], "personality":""}'
        )
        user_prompt = (
            f"Create persona for this professional.\nIndustry: {profile.industry}\n"
            f"Skills: {profile.skills}\nSummary: {profile.summary}\nExperience: {profile.experience}\n"
            f"Content behavior: {behavior}"
        )
        fallback: dict[str, Any] = {
            "tone": "professional",
            "style": "insightful",
            "expertise": profile.skills[:6],
            "personality": "credible and practical",
        }
        persona_json = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)

        persona = db.query(Persona).filter(Persona.user_id == user.id).one_or_none()
        if persona is None:
            persona = Persona(user_id=user.id)
            db.add(persona)

        persona.tone = str(persona_json.get("tone", "professional"))
        persona.style = str(persona_json.get("style", "insightful"))
        persona.expertise = list(persona_json.get("expertise", []))
        persona.personality = str(persona_json.get("personality", "credible and practical"))
        persona.content_behavior = behavior

        db.commit()
        db.refresh(persona)
        return persona
