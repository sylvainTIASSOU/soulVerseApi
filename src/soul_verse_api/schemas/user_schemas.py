from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class User(BaseModel):
    id: UUID                    # UUID unique
    fcm_token: str                  # Token Firebase Cloud Messaging
    phone_model: Optional[str]      # Modèle téléphone (pour debug)
    preferred_translation: str = "FreBBB"  # Traduction Bible préférée
    phone_os: Optional[str]         # Système d'exploitation téléphone
    app_version: Optional[str]      # Version de l'application
    phone_mark: Optional[str]      # Marque du téléphone
    language: str = "fr"            # Langue interface
    timezone: str = "Africa/Lome"   # Fuseau horaire
    mood: Optional[str]             # Dernier mood déclaré
    created_at: datetime

class UserCreate(BaseModel):
    fcm_token: str
    phone_model: Optional[str]
    phone_os: Optional[str]
    app_version: Optional[str]
    phone_mark: Optional[str]

class UserMood(BaseModel):
    id: UUID
    mood: str                       # anxiété, joie, tristesse, etc.
    declared_at: datetime


class UserJournal(BaseModel):
    user_id: UUID
    entry_date: datetime                 # YYYY-MM-DD
    text_content: Optional[str]
    audio_url: Optional[str]        # Lien fichier audio si disponible
    sentiment: Optional[str]        # Analyse de sentiment si disponible
    created_at: datetime
