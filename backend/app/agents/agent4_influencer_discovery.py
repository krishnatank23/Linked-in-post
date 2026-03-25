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
        # Handle variations like www.linkedin.com, in.linkedin.com, etc.
        return "linkedin.com/in/" in value or "linkedin.com/company/" in value

    def _generate_search_queries(self, profile: Profile, persona: Persona) -> list[str]:
        industry = profile.industry or "technology"
        expertise = ", ".join((persona.expertise or [])[:3])
        skills = ", ".join(profile.skills[:5])
        
        system_prompt = (
            "You are an expert at SEO and LinkedIn search optimization. "
            "Generate 4 distinct, high-quality search queries to find top LinkedIn influencers and thought leaders. "
            "Each query must start with 'site:linkedin.com/in '. "
            "Focus on keywords related to the user's industry, expertise, and skills. "
            "Return ONLY a JSON array of strings."
        )
        
        user_prompt = (
            f"Industry: {industry}\n"
            f"Expertise: {expertise}\n"
            f"Skills: {skills}\n"
            "Generate 4 optimized LinkedIn search queries."
        )
        
        try:
            queries = self.groq.complete_json(system_prompt, user_prompt, fallback=[])
            if isinstance(queries, list) and len(queries) >= 2:
                cleaned = []
                for q in queries:
                    q = str(q).strip().strip('"').strip("'")
                    if not q.lower().startswith("site:linkedin.com"):
                        q = f"site:linkedin.com/in {q}"
                    cleaned.append(q)
                return cleaned[:4]
        except Exception:
            pass
            
        return [
            f"site:linkedin.com/in top LinkedIn influencers in {industry}",
            f"site:linkedin.com/in best LinkedIn creators {industry} {expertise}",
            f"site:linkedin.com/in LinkedIn thought leaders {industry} {skills}",
            f"site:linkedin.com/in famous LinkedIn creators {industry}",
        ]

    def _search_candidates(self, profile: Profile, persona: Persona) -> list[dict[str, str]]:
        queries = self._generate_search_queries(profile, persona)

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
        import logging
        logger = logging.getLogger(__name__)
        
        raw_candidates = self._search_candidates(profile=profile, persona=persona)
        
        if not raw_candidates:
            logger.warning(f"No candidates found for user {user.id}")
            return []
        
        linkedin_candidates = [c for c in raw_candidates if self._is_linkedin_profile_link(c.get("profile_link", ""))]
        
        if not linkedin_candidates:
            logger.warning(f"No valid LinkedIn profiles found for user {user.id}")
            return []
            
        candidate_pool = linkedin_candidates
        
        logger.info(f"Found {len(raw_candidates)} total candidates, {len(linkedin_candidates)} LinkedIn profiles")

        system_prompt = (
            "You are an AI expert at identifying and ranking LinkedIn influencers. "
            "Given a list of candidate LinkedIn profiles, filter and rank them based on relevance to the user's industry and expertise. "
            "Return ONLY valid JSON (no markdown, no extra text) as an array of objects with these exact fields:\n"
            '- name (string): full name of influencer\n'
            '- profile_link (string): exact LinkedIn URL from input\n'
            '- description (string): brief description of their expertise\n'
            '- rank_score (integer): 0-100, where 100=most relevant\n\n'
            "IMPORTANT: rank_score must be an integer, not a string. Return exactly the top influencers, no duplicates."
        )
        
        user_prompt = (
            f"User Profile - Industry: {profile.industry or 'not specified'}\n"
            f"User Skills: {', '.join(profile.skills[:10]) if profile.skills else 'not specified'}\n"
            f"User Persona - Tone: {persona.tone}, Style: {persona.style}, Expertise: {', '.join(persona.expertise or [])}\n\n"
            f"Rank these LinkedIn influencers by relevance to the user's profile:\n"
            f"{candidate_pool}\n\n"
            f"Return ONLY a JSON array with the top {min(self.settings.max_influencers, len(candidate_pool))} influencers. "
            f"No markdown, no code blocks, just raw JSON starting with [ and ending with ]."
        )
        
        try:
            ranked = self.groq.complete_json(system_prompt, user_prompt, fallback=[])
        except Exception as e:
            logger.error(f"LLM request failed for user {user.id}: {str(e)}", exc_info=True)
            ranked = []

        if not isinstance(ranked, list):
            logger.warning(f"LLM returned non-list type: {type(ranked)}")
            ranked = []

        if not ranked:
            logger.info(f"LLM returned empty results, using unranked candidates for user {user.id}")
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
            try:
                link = str(item.get("profile_link", "")).strip()
                if not link or not self._is_linkedin_profile_link(link):
                    logger.warning(f"Skipping invalid LinkedIn link: {link}")
                    continue

                name = str(item.get("name", "Unknown")).strip()
                description = str(item.get("description", "")).strip()
                rank_score = item.get("rank_score", 50)
                
                # Validate rank_score is integer
                if isinstance(rank_score, str):
                    try:
                        rank_score = int(rank_score)
                    except ValueError:
                        logger.warning(f"Could not convert rank_score '{rank_score}' to int, using 50")
                        rank_score = 50
                else:
                    rank_score = int(rank_score)
                
                # Ensure rank_score is 0-100
                rank_score = max(0, min(100, rank_score))

                influencer = (
                    db.query(Influencer)
                    .filter(Influencer.user_id == user.id, Influencer.profile_link == link)
                    .one_or_none()
                )
                if influencer is None:
                    influencer = Influencer(user_id=user.id, profile_link=link)
                    db.add(influencer)

                influencer.name = name
                influencer.description = description
                influencer.rank_score = rank_score
                influencers.append(influencer)
                
            except Exception as e:
                logger.error(f"Error processing influencer item {item}: {str(e)}", exc_info=True)
                continue

        try:
            db.commit()
            for influencer in influencers:
                db.refresh(influencer)
            logger.info(f"Successfully stored {len(influencers)} influencers for user {user.id}")
        except Exception as e:
            logger.error(f"Database commit failed for user {user.id}: {str(e)}", exc_info=True)
            db.rollback()
            raise
        
        return influencers
