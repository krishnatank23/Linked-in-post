from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    profiles: Mapped[list["Profile"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    personas: Mapped[list["Persona"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notification_preferences: Mapped[list["NotificationPreference"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    influencers: Mapped[list["Influencer"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    gap_rows: Mapped[list["GapAnalysis"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    generated_content: Mapped[list["GeneratedContent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    experience: Mapped[list[dict]] = mapped_column(JSON, default=list)
    industry: Mapped[str] = mapped_column(String(120), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    past_posts: Mapped[list[dict]] = mapped_column(JSON, default=list)
    media_metadata: Mapped[list[dict]] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship(back_populates="profiles")
    linkedin_cache: Mapped["LinkedInProfileCache"] = relationship(back_populates="profile", uselist=False, cascade="all, delete-orphan")


class LinkedInProfileCache(Base, TimestampMixin):
    """Stores complete LinkedIn profile data extracted at login."""
    __tablename__ = "linkedin_profile_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Personal Info
    full_name: Mapped[str] = mapped_column(String(255), default="")
    headline: Mapped[str] = mapped_column(String(255), default="")  # e.g., "Head of AI ML | 100k+ LinkedIn | AI Agents, RAG, NLP"
    location: Mapped[str] = mapped_column(String(255), default="")  # e.g., "Berlin, Germany"
    
    # Profile Summary
    about: Mapped[str] = mapped_column(Text, default="")  # Full "About" section
    
    # Skills & Expertise
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)  # List of skills e.g., ["Machine Learning", "Python", "AWS"]
    expertise_areas: Mapped[list[str]] = mapped_column(JSON, default=list)  # Main expertise areas
    
    # Experience
    current_position: Mapped[str] = mapped_column(String(255), default="")  # Current job title
    current_company: Mapped[str] = mapped_column(String(255), default="")  # Current company
    years_of_experience: Mapped[int] = mapped_column(Integer, default=0)
    work_history: Mapped[list[dict]] = mapped_column(JSON, default=list)  # List of jobs with dates & descriptions
    
    # Education
    education: Mapped[list[dict]] = mapped_column(JSON, default=list)  # List of education entries
    
    # Follower/Connection Info
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    connection_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Extract all available metadata
    full_profile_data: Mapped[dict] = mapped_column(JSON, default=dict)  # Complete parsed profile for reference
    
    profile: Mapped["Profile"] = relationship(back_populates="linkedin_cache")


class Persona(Base, TimestampMixin):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    tone: Mapped[str] = mapped_column(String(120), default="")
    style: Mapped[str] = mapped_column(String(120), default="")
    expertise: Mapped[list[str]] = mapped_column(JSON, default=list)
    personality: Mapped[str] = mapped_column(String(200), default="")
    content_behavior: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship(back_populates="personas")


class Influencer(Base, TimestampMixin):
    __tablename__ = "influencers"
    __table_args__ = (UniqueConstraint("user_id", "profile_link", name="uq_user_influencer_link"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_link: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    rank_score: Mapped[int] = mapped_column(Integer, default=0)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="influencers")
    analyses: Mapped[list["InfluencerAnalysis"]] = relationship(
        back_populates="influencer", cascade="all, delete-orphan"
    )


class InfluencerAnalysis(Base, TimestampMixin):
    __tablename__ = "influencer_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    influencer_id: Mapped[int] = mapped_column(ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False)

    tone: Mapped[str] = mapped_column(String(120), default="")
    hooks: Mapped[list[str]] = mapped_column(JSON, default=list)
    writing_style: Mapped[str] = mapped_column(String(200), default="")
    content_patterns: Mapped[list[str]] = mapped_column(JSON, default=list)
    growth_strategy: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_items: Mapped[list[dict]] = mapped_column(JSON, default=list)

    influencer: Mapped["Influencer"] = relationship(back_populates="analyses")


class GapAnalysis(Base, TimestampMixin):
    __tablename__ = "gap_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(120), nullable=False)
    user_value: Mapped[str] = mapped_column(Text, default="")
    influencer_value: Mapped[str] = mapped_column(Text, default="")
    gap: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")

    user: Mapped["User"] = relationship(back_populates="gap_rows")


class GeneratedContent(Base, TimestampMixin):
    __tablename__ = "generated_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship(back_populates="generated_content")


class NotificationPreference(Base, TimestampMixin):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    outlook_email: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cadence_days: Mapped[int] = mapped_column(Integer, default=3)
    preferred_hour: Mapped[int] = mapped_column(Integer, default=9)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    preferred_weekdays: Mapped[list[int]] = mapped_column(JSON, default=list)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="notification_preferences")
