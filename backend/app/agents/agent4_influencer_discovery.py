from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Influencer, Persona, Profile, User
from app.services.duckduckgo_client import DuckDuckGoClient
from app.services.groq_client import GroqClient


class InfluencerDiscoveryAgent:
    def __init__(self, groq: GroqClient, ddg: DuckDuckGoClient) -> None:
        self.groq = groq
        self.ddg = ddg
        self.settings = get_settings()

    @staticmethod
    def _is_linkedin_profile_link(link: str) -> bool:
        value = link.lower()
        return "linkedin.com/in/" in value or "linkedin.com/company/" in value

    def _search_candidates(self, industry: str, role_hint: str, persona: Persona) -> list[dict[str, str]]:
        expertise_hint = ", ".join((persona.expertise or [])[:3])
        tone_hint = persona.tone or "professional"
        queries = [
            f"site:linkedin.com/in top LinkedIn influencers in {industry}",
            f"site:linkedin.com/in best LinkedIn creators {role_hint}",
            f"site:linkedin.com/in LinkedIn thought leaders {industry} {expertise_hint}",
            f"site:linkedin.com/in famous LinkedIn creators {industry} {tone_hint}",
        ]

        candidates: list[dict[str, str]] = []
        seen_links: set[str] = set()
        for query in queries:
            rows = self.ddg.search_text(query=query, max_results=15)
            for row in rows:
                link = str(row.get("href", "")).strip()
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                candidates.append(
                    {
                        "name": row.get("title", "Unknown").split("|")[0].strip(),
                        "profile_link": link,
                        "description": row.get("body", ""),
                    }
                )
        return candidates

    def run(self, db: Session, user: User, profile: Profile, persona: Persona) -> list[Influencer]:
        raw_candidates = self._search_candidates(
            industry=profile.industry or "technology",
            role_hint=profile.summary[:80],
            persona=persona,
        )
        linkedin_candidates = [c for c in raw_candidates if self._is_linkedin_profile_link(c.get("profile_link", ""))]
        candidate_pool = linkedin_candidates or raw_candidates

        system_prompt = (
            "You filter and rank LinkedIn influencers. Prioritize real LinkedIn profile URLs. "
            "Return strict JSON array of objects with keys: "
            "name, profile_link, description, rank_score (0-100)."
        )
        user_prompt = (
            f"User industry: {profile.industry}\nUser skills: {profile.skills}\n"
            f"User persona: tone={persona.tone}, style={persona.style}, expertise={persona.expertise}\n"
            f"Candidate influencers: {candidate_pool}\n"
            f"Return top {self.settings.max_influencers}."
        )
        fallback: list[dict[str, Any]] = []
        ranked = self.groq.complete_json(system_prompt, user_prompt, fallback=fallback)

        if not isinstance(ranked, list):
            ranked = []

        if not ranked:
            ranked = [
                {
                    "name": c.get("name", "Unknown"),
                    "profile_link": c.get("profile_link", ""),
                    "description": c.get("description", ""),
                    "rank_score": 50,
                }
                for c in candidate_pool[: self.settings.max_influencers]
            ]

        influencers: list[Influencer] = []
        for item in ranked[: self.settings.max_influencers]:
            link = str(item.get("profile_link", "")).strip()
            if not link:
                continue

            influencer = (
                db.query(Influencer)
                .filter(Influencer.user_id == user.id, Influencer.profile_link == link)
                .one_or_none()
            )
            if influencer is None:
                influencer = Influencer(user_id=user.id, profile_link=link)
                db.add(influencer)

            influencer.name = str(item.get("name", "Unknown"))
            influencer.description = str(item.get("description", ""))
            influencer.rank_score = int(item.get("rank_score", 50))
            influencers.append(influencer)

        db.commit()
        for influencer in influencers:
            db.refresh(influencer)
        return influencers
