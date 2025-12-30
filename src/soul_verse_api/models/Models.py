from sqlalchemy import Boolean, Column, ForeignKey, Numeric, String, DateTime
from sqlalchemy.sql import func

from sqlalchemy.orm import relationship
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

from src.soul_verse_api.database.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False
    )
    fcm_token = Column(String, unique=True, index=True, nullable=True)
    phone_model = Column(String, nullable=True)
    preferred_translation = Column(String, nullable=True, default="FreBBB")
    phone_os = Column(String, nullable=True)
    app_version = Column(String, nullable=True)
    phone_mark = Column(String, nullable=True)
    language = Column(String, nullable=True, default="fr")
    timezone = Column(String, nullable=True, default="Africa/Lome")
    mood = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True)
    journals = relationship("UserJournal", back_populates="user")


class UserJournal(Base):
    __tablename__ = "user_journals"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    text_content = Column(String, nullable=False)
    entry_date = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    audio_url = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="journals")


class BibleVerse(Base):
    __tablename__ = "bible_verses"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False
    )
    book = Column(String, nullable=False)
    chapter = Column(Numeric, nullable=False)
    verse = Column(Numeric, nullable=False)
    text = Column(String, nullable=False)
    translation = Column(String, nullable=False, default="FreBBB")
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)


class VerseWithReflection(Base):
    __tablename__ = "verses_with_reflections"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False
    )
    verse_id = Column(
        UUID(as_uuid=True), ForeignKey("bible_verses.id"), nullable=False, index=True
    )
    reflection = Column(String, nullable=True)
    mood_context = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    verse = relationship("BibleVerse")


class DailyVerseDelivery(Base):
    __tablename__ = "daily_verse_deliveries"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    verse_with_reflection_id = Column(
        UUID(as_uuid=True), ForeignKey("verses_with_reflections.id"), nullable=False, index=True
    )
    date = Column(DateTime(timezone=True),
                      server_default=func.now(), nullable=False)
    cached_at = Column(DateTime(timezone=True),
                       server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    user = relationship("User")
    verse_with_reflection = relationship("VerseWithReflection")
