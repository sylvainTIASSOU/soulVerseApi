from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class BibleVerse(BaseModel):
    book: str                       # "Genesis", "Matthew", etc.
    chapter: int
    verse: int
    text: str
    translation: str                # "FreBBB", "KJV", etc.


class VerseImage(BaseModel):
    """Modèle pour les images de versets"""
    image_url: str
    image_path: Optional[str] = None
    image_hash: str
    generation_method: str           # "local", "dalle", "stability", "cached"
    generated_at: datetime
    mood_theme: Optional[str] = None


class VerseWithReflection(BaseModel):
    verse_id: UUID
    verse: BibleVerse
    ai_reflection: str              # Réflexion générée par IA
    verse_image: Optional[VerseImage] = None  # Image générée pour le verset
    mood_context: Optional[str] = None     # Mood ayant inspiré le verset
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DailyVerseResponse(BaseModel):
    """Réponse complète pour verset quotidien"""
    verse: BibleVerse
    ai_reflection: str
    verse_image: Optional[VerseImage] = None
    mood_context: str
    reference: str
    generated_at: datetime
    user_id: str
    translation: str
    test_mode: Optional[bool] = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DailyVerseCache(BaseModel):
    user_id: UUID
    verse_with_reflection_id: UUID
    date: datetime                       # YYYY-MM-DD
    verse_with_reflection: VerseWithReflection
    cached_at: datetime
    expires_at: datetime            # 2h après création


class VerseGenerationRequest(BaseModel):
    """Request pour génération de verset personnalisé"""
    mood: str = "paix"
    translation: str = "FreBBB"
    include_image: bool = True
    image_method: str = "auto"  # "auto", "local", "dalle", "stability"


class BulkVerseResponse(BaseModel):
    """Réponse pour génération en masse"""
    success: bool
    message: str
    statistics: Dict[str, Any]
    results: List[Dict[str, Any]]
    note: Optional[str] = None
    timestamp: datetime
