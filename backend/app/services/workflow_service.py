import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.agents.agent10_post_humanizer import PostHumanizerAgent
from app.agents.agent2_user_persona import UserPersonaAgent
from app.agents.agent3_content_behavior import ContentBehaviorAgent
from app.agents.agent4_influencer_discovery import InfluencerDiscoveryAgent
from app.agents.agent5_influencer_intelligence import InfluencerIntelligenceAgent
from app.agents.agent6_gap_analysis import GapAnalysisAgent
from app.agents.agent7_content_strategy import ContentStrategyAgent
from app.agents.agent8_post_generation import PostGenerationAgent
from app.db.models import Influencer, Profile, User
from app.services.duckduckgo_client import DuckDuckGoClient
from app.services.groq_client import GroqClient

logger = logging.getLogger(__name__)

class WorkflowService:
    def __init__(self) -> None:
        self.groq = GroqClient()
        self.ddg = DuckDuckGoClient()
        
        self.persona_agent = UserPersonaAgent(groq=self.groq)
        self.behavior_agent = ContentBehaviorAgent(groq=self.groq)
        self.discovery_agent = InfluencerDiscoveryAgent(groq=self.groq, ddg=self.ddg)
        self.intelligence_agent = InfluencerIntelligenceAgent(groq=self.groq, ddg=self.ddg)
        self.gap_agent = GapAnalysisAgent(groq=self.groq)
        self.strategy_agent = ContentStrategyAgent(groq=self.groq)
        self.post_agent = PostGenerationAgent(groq=self.groq)
        self.humanizer_agent = PostHumanizerAgent(groq=self.groq)

    def run_full_pipeline(self, db: Session, user: User) -> List[Dict[str, Any]]:
        results = []
        
        profile = (
            db.query(Profile)
            .filter(Profile.user_id == user.id)
            .order_by(Profile.created_at.desc())
            .first()
        )
        if profile is None:
            return [{"step": "Pre-check", "status": "error", "error": "Profile not found. Upload profile first."}]

        # Step 2: User Persona
        results.append(self._run_step(2, "User Persona", self.persona_agent.run, db=db, user=user, profile=profile))
        persona = results[-1].get("output")
        
        # Step 3: Content Behavior
        if persona:
            results.append(self._run_step(3, "Content Behavior", self.behavior_agent.run, db=db, profile=profile, persona=persona))
        else:
            results.append({"step": 3, "name": "Content Behavior", "status": "skipped", "error": "Dependent persona step failed"})

        # Step 4: Influencer Discovery
        if persona:
            results.append(self._run_step(4, "Influencer Discovery", self.discovery_agent.run, db=db, user=user, profile=profile, persona=persona))
            influencers = results[-1].get("output", [])
        else:
            results.append({"step": 4, "name": "Influencer Discovery", "status": "skipped", "error": "Dependent persona step failed"})
            influencers = []

        # Ensure some influencers are selected for the next steps
        if persona and influencers:
            # Auto-select top 5 if none are selected
            selected = [i for i in influencers if i.selected]
            if not selected:
                for i in influencers[:5]:
                    i.selected = True
                db.commit()
                selected = influencers[:5]
        else:
            selected = []

        # Step 5: Influencer Intelligence
        if selected:
            results.append(self._run_step(5, "Influencer Intelligence", self.intelligence_agent.run, db=db, influencers=selected))
            analyses = results[-1].get("output")
        else:
            results.append({"step": 5, "name": "Influencer Intelligence", "status": "skipped", "error": "No influencers found or selected"})
            analyses = None

        # Step 6: Gap Analysis
        if persona and selected and analyses:
            results.append(self._run_step(6, "Gap Analysis", self.gap_agent.run, db=db, user=user, persona=persona, influencers=selected, analyses=analyses))
            gaps = results[-1].get("output")
        else:
            results.append({"step": 6, "name": "Gap Analysis", "status": "skipped", "error": "Dependent steps failed"})
            gaps = None

        # Step 7: Content Strategy
        if persona and profile and gaps:
            results.append(self._run_step(7, "Content Strategy", self.strategy_agent.run, db=db, user=user, profile=profile, persona=persona, gap_rows=gaps))
        else:
            results.append({"step": 7, "name": "Content Strategy", "status": "skipped", "error": "Dependent steps failed"})

        return results

    def _run_step(self, step_id: int, name: str, func, **kwargs) -> Dict[str, Any]:
        try:
            output = func(**kwargs)
            # Serialize output if it's a DB model
            serializable_output = self._serialize(output)
            return {"step": step_id, "name": name, "status": "success", "output": serializable_output}
        except Exception as e:
            logger.exception(f"Error in step {step_id}: {name}")
            return {"step": step_id, "name": name, "status": "error", "error": str(e)}

    def _serialize(self, obj: Any) -> Any:
        if isinstance(obj, list):
            return [self._serialize(i) for i in obj]
        if hasattr(obj, "__dict__"):
            # Simple serialization for SQLAlchemy models or custom objects
            # We only want basic data fields
            data = {}
            for key, value in obj.__dict__.items():
                if not key.startswith("_"):
                    if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                        data[key] = value
                    else:
                        data[key] = str(value)
            return data
        return obj
