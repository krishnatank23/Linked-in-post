from sqlalchemy.orm import Session

from app.db.models import GapAnalysis, Influencer, InfluencerAnalysis, Persona, User
from app.services.groq_client import GroqClient


class GapAnalysisAgent:
    def __init__(self, groq: GroqClient) -> None:
        self.groq = groq

    def run(
        self,
        db: Session,
        user: User,
        persona: Persona,
        influencers: list[Influencer],
        analyses: list[InfluencerAnalysis],
    ) -> list[GapAnalysis]:
        avg_reference = [
            {
                "influencer": i.name,
                "tone": a.tone,
                "writing_style": a.writing_style,
                "content_patterns": a.content_patterns,
                "growth_strategy": a.growth_strategy,
            }
            for i in influencers
            for a in analyses
            if a.influencer_id == i.id
        ]

        system_prompt = (
            "Compare a user persona to influencer benchmarks and return strict JSON array of objects with keys: "
            "category, user, influencer, gap, recommendation."
        )
        user_prompt = (
            f"User persona: tone={persona.tone}, style={persona.style}, expertise={persona.expertise}, behavior={persona.content_behavior}\n"
            f"Influencer reference: {avg_reference}"
        )
        fallback = [
            {
                "category": "Content Consistency",
                "user": "No fixed publishing cadence",
                "influencer": "3-5 posts per week",
                "gap": "Inconsistent content rhythm",
                "recommendation": "Adopt a weekly cadence with recurring themes",
            }
        ]
        rows = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)

        db.query(GapAnalysis).filter(GapAnalysis.user_id == user.id).delete()
        db.commit()

        stored_rows: list[GapAnalysis] = []
        if not isinstance(rows, list):
            rows = fallback

        for item in rows:
            row = GapAnalysis(
                user_id=user.id,
                category=str(item.get("category", "General")),
                user_value=str(item.get("user", "")),
                influencer_value=str(item.get("influencer", "")),
                gap=str(item.get("gap", "")),
                recommendation=str(item.get("recommendation", "")),
            )
            db.add(row)
            stored_rows.append(row)

        db.commit()
        for row in stored_rows:
            db.refresh(row)
        return stored_rows
