from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Influencer, InfluencerAnalysis
from app.services.duckduckgo_client import DuckDuckGoClient
from app.services.groq_client import GroqClient


class InfluencerIntelligenceAgent:
    def __init__(self, groq: GroqClient, ddg: DuckDuckGoClient) -> None:
        self.groq = groq
        self.ddg = ddg

    def run(self, db: Session, influencers: list[Influencer]) -> list[InfluencerAnalysis]:
        analyses: list[InfluencerAnalysis] = []

        for influencer in influencers:
            linkedin_link = influencer.profile_link if "linkedin.com" in influencer.profile_link.lower() else ""
            queries = [
                f"site:linkedin.com/in {influencer.name} LinkedIn profile",
                f"{influencer.name} LinkedIn posts",
                f"{influencer.name} LinkedIn article",
                f"{influencer.name} interview branding strategy",
            ]
            if linkedin_link:
                queries.insert(1, linkedin_link)

            source_items: list[dict[str, Any]] = []
            for query in queries:
                source_items.extend(self.ddg.search_text(query=query, max_results=5))

            linkedin_sources = [
                item
                for item in source_items
                if "linkedin.com" in str(item.get("href", "")).lower()
                or "linkedin" in str(item.get("title", "")).lower()
            ]
            web_sources = [item for item in source_items if item not in linkedin_sources]
            prioritized_sources = linkedin_sources + web_sources

            system_prompt = (
                "Extract influencer content intelligence with a LinkedIn-first perspective. "
                "Return strict JSON object with keys: "
                "tone (string), hooks (array), writing_style (string), content_patterns (array), growth_strategy (array)."
            )
            user_prompt = (
                f"Influencer: {influencer.name}\n"
                f"Known LinkedIn profile: {linkedin_link or 'not provided'}\n"
                f"Description: {influencer.description}\n"
                f"LinkedIn-focused web data: {prioritized_sources}"
            )
            fallback = {
                "tone": "professional",
                "hooks": ["Contrarian insight", "Short personal story"],
                "writing_style": "concise and example-driven",
                "content_patterns": ["How-to posts", "Framework posts"],
                "growth_strategy": ["Consistency", "Engagement in comments"],
            }
            parsed = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)

            analysis = (
                db.query(InfluencerAnalysis)
                .filter(InfluencerAnalysis.influencer_id == influencer.id)
                .one_or_none()
            )
            if analysis is None:
                analysis = InfluencerAnalysis(influencer_id=influencer.id)
                db.add(analysis)

            analysis.tone = str(parsed.get("tone", "professional"))
            analysis.hooks = list(parsed.get("hooks", []))
            analysis.writing_style = str(parsed.get("writing_style", ""))
            analysis.content_patterns = list(parsed.get("content_patterns", []))
            analysis.growth_strategy = list(parsed.get("growth_strategy", []))
            analysis.source_items = prioritized_sources
            analyses.append(analysis)

        db.commit()
        for item in analyses:
            db.refresh(item)
        return analyses
