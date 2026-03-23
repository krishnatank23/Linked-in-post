import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.agents.agent1_profile_ingestion import ProfileIngestionAgent
from app.agents.agent10_post_humanizer import PostHumanizerAgent
from app.agents.agent11_notification_scheduler import NotificationSchedulerAgent
from app.agents.agent2_user_persona import UserPersonaAgent
from app.agents.agent4_influencer_discovery import InfluencerDiscoveryAgent
from app.agents.agent5_influencer_intelligence import InfluencerIntelligenceAgent
from app.agents.agent6_gap_analysis import GapAnalysisAgent
from app.agents.agent7_content_strategy import ContentStrategyAgent
from app.agents.agent8_post_generation import PostGenerationAgent
from app.agents.agent9_notification_manager import NotificationManagerAgent
from app.db.models import GapAnalysis, GeneratedContent, Influencer, NotificationPreference, Profile, User
from app.db.session import get_db
from app.orchestrator.analysis_service import AnalysisOrchestrator
from app.schemas.api import (
    GapRowOut,
    GeneratePostRequest,
    GenerateStrategyRequest,
    InfluencerOut,
    LoginRequest,
    LoginResponse,
    NotificationSettingsRequest,
    NotificationSettingsResponse,
    RegisterRequest,
    RegisterResponse,
    RunAnalysisRequest,
    SendNotificationRequest,
    SelectInfluencersRequest,
)
from app.services.duckduckgo_client import DuckDuckGoClient
from app.services.groq_client import GroqClient
from app.services.outlook_mailer import OutlookMailer
from app.services.parsers import flatten_linkedin_json, parse_docx_text, parse_linkedin_json, parse_pdf_text
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter()


def build_orchestrator() -> AnalysisOrchestrator:
    groq = GroqClient()
    ddg = DuckDuckGoClient()
    return AnalysisOrchestrator(
        persona_agent=UserPersonaAgent(groq=groq),
        discovery_agent=InfluencerDiscoveryAgent(groq=groq, ddg=ddg),
        intelligence_agent=InfluencerIntelligenceAgent(groq=groq, ddg=ddg),
        gap_agent=GapAnalysisAgent(groq=groq),
    )


@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    existing = db.query(User).filter(User.email == payload.email).one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    password_hash = hash_password(payload.password)
    user = User(email=payload.email, full_name=payload.full_name, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return RegisterResponse(user_id=user.id, email=user.email, full_name=user.full_name)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found. Please register first.")

    # Backward compatibility for users created before password hashing existed.
    if not (user.password_hash or "").strip():
        user.password_hash = hash_password(payload.password)
        db.commit()
        db.refresh(user)
        return LoginResponse(user_id=user.id, email=user.email, full_name=user.full_name)

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")

    return LoginResponse(user_id=user.id, email=user.email, full_name=user.full_name)


@router.post("/upload-profile")
async def upload_profile(
    user_id: int = Form(...),
    profile_file: UploadFile = File(...),
    past_posts_json: str | None = Form(default=None),
    media_metadata_json: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    content = await profile_file.read()
    filename = (profile_file.filename or "").lower()

    source_type: str
    raw_text: str

    try:
        if filename.endswith(".json"):
            data = parse_linkedin_json(content)
            raw_text = flatten_linkedin_json(data)
            source_type = "linkedin_json"
        elif filename.endswith(".pdf"):
            try:
                raw_text = parse_pdf_text(content)
            except Exception:
                logger.warning("PDF text extraction failed; falling back to filename/context", exc_info=True)
                raw_text = f"Uploaded resume PDF: {profile_file.filename}. Text extraction unavailable."
            source_type = "resume_pdf"
        elif filename.endswith(".docx"):
            try:
                raw_text = parse_docx_text(content)
            except Exception:
                logger.warning("DOCX text extraction failed; falling back to filename/context", exc_info=True)
                raw_text = f"Uploaded resume DOCX: {profile_file.filename}. Text extraction unavailable."
            source_type = "resume_docx"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Use JSON, PDF, or DOCX.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to parse uploaded file")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to parse profile file") from exc

    try:
        past_posts = json.loads(past_posts_json) if past_posts_json else []
        media_metadata = json.loads(media_metadata_json) if media_metadata_json else []
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON in optional fields") from exc

    ingestion = ProfileIngestionAgent(groq=GroqClient())
    profile = ingestion.run(
        db=db,
        user=user,
        source_type=source_type,
        raw_text=raw_text,
        past_posts=past_posts,
        media_metadata=media_metadata,
    )

    return {
        "profile_id": profile.id,
        "source_type": profile.source_type,
        "industry": profile.industry,
        "skills_count": len(profile.skills),
    }


@router.post("/run-analysis")
def run_analysis(payload: RunAnalysisRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    orchestrator = build_orchestrator()
    try:
        return orchestrator.run(db=db, user=user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/profile-status")
def profile_status(user_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user_id)
        .order_by(Profile.created_at.desc())
        .first()
    )

    return {
        "user_id": user_id,
        "has_profile": profile is not None,
        "profile_id": profile.id if profile else None,
        "source_type": profile.source_type if profile else None,
    }


@router.get("/influencers", response_model=list[InfluencerOut])
def get_influencers(user_id: int, db: Session = Depends(get_db)) -> list[InfluencerOut]:
    rows = (
        db.query(Influencer)
        .filter(Influencer.user_id == user_id)
        .order_by(Influencer.rank_score.desc(), Influencer.created_at.desc())
        .all()
    )
    return [
        InfluencerOut(
            id=row.id,
            name=row.name,
            profile_link=row.profile_link,
            description=row.description,
            rank_score=row.rank_score,
            selected=row.selected,
        )
        for row in rows
    ]


@router.post("/select-influencers")
def select_influencers(payload: SelectInfluencersRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    orchestrator = build_orchestrator()
    rows = orchestrator.select_influencers(db=db, user=user, influencer_ids=payload.influencer_ids)
    selected_count = len([row for row in rows if row.selected])
    return {"selected_count": selected_count}


@router.get("/gap-analysis", response_model=list[GapRowOut])
def get_gap_analysis(user_id: int, db: Session = Depends(get_db)) -> list[GapRowOut]:
    rows = db.query(GapAnalysis).filter(GapAnalysis.user_id == user_id).all()
    return [
        GapRowOut(
            category=row.category,
            user=row.user_value,
            influencer=row.influencer_value,
            gap=row.gap,
            recommendation=row.recommendation,
        )
        for row in rows
    ]


@router.post("/generate-strategy")
def generate_strategy(payload: GenerateStrategyRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user.id)
        .order_by(Profile.created_at.desc())
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload profile first")

    orchestrator = build_orchestrator()
    persona = orchestrator.get_persona(db, user.id)
    if persona is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run analysis first")

    gap_rows = db.query(GapAnalysis).filter(GapAnalysis.user_id == user.id).all()
    strategy_agent = ContentStrategyAgent(groq=GroqClient())
    content = strategy_agent.run(db=db, user=user, profile=profile, persona=persona, gap_rows=gap_rows)
    return {"content_id": content.id, "strategy": content.payload}


@router.post("/generate-post")
def generate_post(payload: GeneratePostRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user.id)
        .order_by(Profile.created_at.desc())
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload profile first")

    orchestrator = build_orchestrator()
    persona = orchestrator.get_persona(db, user.id)
    if persona is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run analysis first")

    post_agent = PostGenerationAgent(groq=GroqClient())
    content = post_agent.run(
        db=db,
        user=user,
        profile=profile,
        persona=persona,
        topic=payload.topic,
        objective=payload.objective,
        media_context=payload.media_context,
    )
    humanizer = PostHumanizerAgent(groq=GroqClient())
    humanized = humanizer.run(payload=content.payload, persona=persona)
    content.payload = humanized
    db.commit()
    db.refresh(content)
    return {"content_id": content.id, "post": content.payload}


@router.post("/notification-settings", response_model=NotificationSettingsResponse)
def upsert_notification_settings(
    payload: NotificationSettingsRequest, db: Session = Depends(get_db)
) -> NotificationSettingsResponse:
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    notification_manager = NotificationManagerAgent()
    settings_row = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == payload.user_id)
        .one_or_none()
    )
    if settings_row is None:
        settings_row = NotificationPreference(user_id=payload.user_id)
        db.add(settings_row)

    cadence_days = min(payload.cadence_days, notification_manager.benchmark_cadence_days(db, payload.user_id))
    settings_row.outlook_email = payload.outlook_email
    settings_row.enabled = payload.enabled
    settings_row.cadence_days = cadence_days
    settings_row.preferred_hour = payload.preferred_hour
    settings_row.timezone = payload.timezone
    settings_row.preferred_weekdays = [int(day) for day in payload.preferred_weekdays if 0 <= int(day) <= 6]
    if not settings_row.preferred_weekdays:
        settings_row.preferred_weekdays = [0, 1, 2, 3, 4]

    db.commit()
    db.refresh(settings_row)

    return NotificationSettingsResponse(
        user_id=settings_row.user_id,
        outlook_email=settings_row.outlook_email,
        enabled=settings_row.enabled,
        cadence_days=settings_row.cadence_days,
        preferred_hour=settings_row.preferred_hour,
        timezone=settings_row.timezone,
        preferred_weekdays=list(settings_row.preferred_weekdays or []),
    )


@router.post("/send-post-notification")
def send_post_notification(payload: SendNotificationRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    notification_manager = NotificationManagerAgent()
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    pref = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == payload.user_id)
        .one_or_none()
    )
    if pref is None or not pref.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enable notification settings first")

    is_due, next_due = notification_manager.is_due(pref=pref, force_send=payload.force_send)
    if not is_due:
        return {
            "sent": False,
            "detail": "Notification is not due yet",
            "next_due_at": next_due.isoformat() if next_due else None,
        }

    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user.id)
        .order_by(Profile.created_at.desc())
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload profile first")

    orchestrator = build_orchestrator()
    persona = orchestrator.get_persona(db, user.id)
    if persona is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run analysis first")

    topic = notification_manager.pick_notification_topic(
        db=db,
        user_id=user.id,
        fallback_topic=f"{profile.industry or 'Industry'} insights",
    )
    post_agent = PostGenerationAgent(groq=GroqClient())
    content = post_agent.run(
        db=db,
        user=user,
        profile=profile,
        persona=persona,
        topic=topic,
        objective="benchmark-aligned posting reminder",
        media_context=None,
    )

    humanizer = PostHumanizerAgent(groq=GroqClient())
    humanized = humanizer.run(payload=content.payload, persona=persona)
    content.payload = humanized
    db.commit()
    db.refresh(content)

    mailer = OutlookMailer()
    email_body = notification_manager.build_ready_post_email(
        user_name=user.full_name,
        topic=topic,
        post_payload=content.payload,
        cadence_days=pref.cadence_days,
    )
    subject = f"LinkedIn Ready Post Reminder for {user.full_name}"

    try:
        mailer.send_post_notification(to_email=pref.outlook_email, subject=subject, body=email_body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed sending Outlook notification")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send email") from exc

    notification_manager.mark_sent(db=db, pref=pref)

    return {
        "sent": True,
        "email": pref.outlook_email,
        "topic": topic,
        "post": content.payload,
    }


@router.post("/dispatch-due-notifications")
def dispatch_due_notifications(db: Session = Depends(get_db)) -> dict[str, Any]:
    due_rows = db.query(NotificationPreference).filter(NotificationPreference.enabled.is_(True)).all()
    sent_count = 0
    skipped_count = 0
    errors: list[dict[str, Any]] = []
    scheduler = NotificationSchedulerAgent()

    for pref in due_rows:
        try:
            should_send, reason = scheduler.should_dispatch_now(pref)
            if not should_send:
                skipped_count += 1
                continue

            req = SendNotificationRequest(user_id=pref.user_id, force_send=False)
            result = send_post_notification(payload=req, db=db)
            if result.get("sent"):
                sent_count += 1
            else:
                skipped_count += 1
        except Exception as exc:
            skipped_count += 1
            errors.append({"user_id": pref.user_id, "detail": str(exc)})

    return {
        "enabled_users": len(due_rows),
        "sent_count": sent_count,
        "skipped_count": skipped_count,
        "errors": errors,
    }
