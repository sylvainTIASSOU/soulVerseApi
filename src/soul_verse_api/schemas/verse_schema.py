from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class BibleVerse(BaseModel):
    book: str                       # "Genesis", "Matthew", etc.
    chapter: int
    verse: int
    text: str
    translation: str                # "FreBBB", "KJV", etc.


class VerseWithReflection(BaseModel):
    verse_id: UUID
    verse: BibleVerse
    reflection: str              # Réflexion générée par IA
    mood_context: Optional[str]     # Mood ayant inspiré le verset
    created_at: datetime


class DailyVerseCache(BaseModel):
    user_id: UUID
    verse_with_reflection_id: UUID
    date: datetime                       # YYYY-MM-DD
    verse_with_reflection: VerseWithReflection
    cached_at: datetime
    expires_at: datetime            # 2h après création
