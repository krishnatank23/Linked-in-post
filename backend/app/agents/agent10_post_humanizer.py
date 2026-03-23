from app.db.models import Persona
from app.services.groq_client import GroqClient


class PostHumanizerAgent:
    def __init__(self, groq: GroqClient) -> None:
        self.groq = groq

    def run(self, payload: dict, persona: Persona) -> dict:
        system_prompt = (
            "Humanize this LinkedIn post while preserving meaning and structure. "
            "Return strict JSON with keys: hook, body, cta, hashtags (array)."
        )
        user_prompt = (
            f"Persona tone: {persona.tone}\n"
            f"Persona style: {persona.style}\n"
            f"Draft post JSON: {payload}\n"
            "Make it feel natural, authentic, and less robotic."
        )
        fallback = payload
        parsed = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)
        if not isinstance(parsed, dict):
            return payload
        return parsed
