from sqlalchemy.orm import Session

from app.db.models import GapAnalysis, GeneratedContent, Persona, Profile, User
from app.services.groq_client import GroqClient


class ContentStrategyAgent:
    def __init__(self, groq: GroqClient) -> None:
        self.groq = groq

    def run(
        self,
        db: Session,
        user: User,
        profile: Profile,
        persona: Persona,
        gap_rows: list[GapAnalysis],
    ) -> GeneratedContent:
        system_prompt = (
            "Create a LinkedIn strategy and return strict JSON object with keys: "
            "content_pillars (array), weekly_calendar (array of objects), post_ideas (array)."
        )
        user_prompt = (
            f"Industry: {profile.industry}\nSkills: {profile.skills}\nPersona: tone={persona.tone}, style={persona.style}\n"
            f"Gap rows: {[{'category': g.category, 'gap': g.gap, 'recommendation': g.recommendation} for g in gap_rows]}"
        )
        fallback = {
            "content_pillars": ["Industry Insights", "Career Lessons", "Practical Frameworks"],
            "weekly_calendar": [
                {"day": "Monday", "theme": "Insight post", "format": "Text"},
                {"day": "Wednesday", "theme": "Case study", "format": "Carousel"},
                {"day": "Friday", "theme": "Personal reflection", "format": "Text"},
            ],
            "post_ideas": [
                "3 mistakes professionals make in personal branding",
                "A simple framework to write higher-performing LinkedIn hooks",
                "What I learned from 5 years in the industry",
            ],
        }
        payload = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)

        content = GeneratedContent(
            user_id=user.id,
            content_type="strategy",
            title="Weekly LinkedIn Strategy",
            payload=payload,
        )
        db.add(content)
        db.commit()
        db.refresh(content)
        return content
