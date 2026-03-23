from sqlalchemy.orm import Session

from app.db.models import GeneratedContent, Persona, Profile, User
from app.services.groq_client import GroqClient


class PostGenerationAgent:
    def __init__(self, groq: GroqClient) -> None:
        self.groq = groq

    def _humanize_post(self, payload: dict, persona: Persona) -> dict:
        system_prompt = (
            "Humanize this LinkedIn post while preserving meaning and structure. "
            "Return strict JSON with keys: hook, body, cta, hashtags (array)."
        )
        user_prompt = (
            f"Persona tone: {persona.tone}\nPersona style: {persona.style}\n"
            f"Draft post JSON: {payload}\n"
            "Make it feel natural, authentic, and less robotic."
        )
        fallback = payload
        parsed = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)
        if not isinstance(parsed, dict):
            return payload
        return parsed

    def run(
        self,
        db: Session,
        user: User,
        profile: Profile,
        persona: Persona,
        topic: str,
        objective: str,
        media_context: str | None = None,
    ) -> GeneratedContent:
        system_prompt = (
            "Generate a LinkedIn post and return strict JSON object with keys: "
            "hook, body, cta, hashtags (array)."
        )
        user_prompt = (
            f"Topic: {topic}\nObjective: {objective}\nIndustry: {profile.industry}\n"
            f"Tone: {persona.tone}\nStyle: {persona.style}\nExpertise: {persona.expertise}\n"
            f"Media context: {media_context or 'None'}"
        )
        fallback = {
            "hook": f"Most professionals underestimate this about {topic}.",
            "body": (
                "A simple shift in approach can dramatically improve visibility and trust. "
                "Start with one practical insight, add one personal lesson, and finish with one clear takeaway."
            ),
            "cta": "What is one tactic that has worked for you?",
            "hashtags": ["#LinkedIn", "#PersonalBranding", "#CareerGrowth"],
        }
        payload = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)
        if not isinstance(payload, dict):
            payload = fallback
        payload = self._humanize_post(payload=payload, persona=persona)

        content = GeneratedContent(
            user_id=user.id,
            content_type="post",
            title=f"LinkedIn Post: {topic}",
            payload=payload,
        )
        db.add(content)
        db.commit()
        db.refresh(content)
        return content
