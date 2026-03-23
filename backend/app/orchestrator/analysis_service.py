from sqlalchemy.orm import Session

from app.agents.agent2_user_persona import UserPersonaAgent
from app.agents.agent4_influencer_discovery import InfluencerDiscoveryAgent
from app.agents.agent5_influencer_intelligence import InfluencerIntelligenceAgent
from app.agents.agent6_gap_analysis import GapAnalysisAgent
from app.db.models import Influencer, Persona, Profile, User


class AnalysisOrchestrator:
    def __init__(
        self,
        persona_agent: UserPersonaAgent,
        discovery_agent: InfluencerDiscoveryAgent,
        intelligence_agent: InfluencerIntelligenceAgent,
        gap_agent: GapAnalysisAgent,
    ) -> None:
        self.persona_agent = persona_agent
        self.discovery_agent = discovery_agent
        self.intelligence_agent = intelligence_agent
        self.gap_agent = gap_agent

    def run(self, db: Session, user: User) -> dict:
        profile = (
            db.query(Profile)
            .filter(Profile.user_id == user.id)
            .order_by(Profile.created_at.desc())
            .first()
        )
        if profile is None:
            raise ValueError("Profile not found. Please upload profile first.")

        persona = self.persona_agent.run(db=db, user=user, profile=profile)
        behavior = persona.content_behavior or {}
        influencers = self.discovery_agent.run(db=db, user=user, profile=profile, persona=persona)

        selected = [i for i in influencers if i.selected]
        analysis_targets = selected or influencers[:10]

        analyses = self.intelligence_agent.run(db=db, influencers=analysis_targets)
        gaps = self.gap_agent.run(
            db=db,
            user=user,
            persona=persona,
            influencers=analysis_targets,
            analyses=analyses,
        )

        return {
            "persona_id": persona.id,
            "influencer_count": len(influencers),
            "analyzed_influencers": len(analysis_targets),
            "gap_rows": len(gaps),
            "behavior": behavior,
        }

    def select_influencers(self, db: Session, user: User, influencer_ids: list[int]) -> list[Influencer]:
        influencers = db.query(Influencer).filter(Influencer.user_id == user.id).all()
        chosen = set(influencer_ids)
        for influencer in influencers:
            influencer.selected = influencer.id in chosen
        db.commit()
        for influencer in influencers:
            db.refresh(influencer)
        return influencers

    @staticmethod
    def get_persona(db: Session, user_id: int) -> Persona | None:
        return db.query(Persona).filter(Persona.user_id == user_id).one_or_none()
