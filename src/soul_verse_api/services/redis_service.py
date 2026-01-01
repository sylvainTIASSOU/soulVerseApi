

# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.soul_verse_api.core.redis_client import get_redis


class RedisService:
    """Service Redis pour la gestion des données de l'application Soul Verse"""

    def __init__(self):
        self.redis_client = get_redis()
        # Durées de cache (en secondes)
        self.DAILY_VERSE_TTL = 7200  # 2 heures
        self.USER_MOOD_TTL = 86400   # 24 heures
        self.USER_DATA_TTL = 604800  # 7 jours

    async def get_daily_verse(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le verset quotidien en cache pour un utilisateur

        Args:
            user_id: ID de l'utilisateur

        Returns:
            Dict contenant le verset et ses métadonnées ou None
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"daily_verse:{user_id}:{today}"

        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        return None

    async def cache_daily_verse(self, user_id: str, verse_data: Dict[str, Any]) -> bool:
        """
        Met en cache le verset quotidien d'un utilisateur

        Args:
            user_id: ID de l'utilisateur
            verse_data: Données du verset avec métadonnées

        Returns:
            True si le cache a réussi, False sinon
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"daily_verse:{user_id}:{today}"

        return self.redis_client.set(cache_key, verse_data, self.DAILY_VERSE_TTL)

    async def delete_daily_verse(self, user_id: str) -> bool:
        """
        Supprime le verset quotidien en cache pour un utilisateur

        Args:
            user_id: ID de l'utilisateur

        Returns:
            True si la suppression a réussi, False sinon
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"daily_verse:{user_id}:{today}"

        return self.redis_client.delete(cache_key)

    async def get_user_mood(self, user_id: str) -> Optional[str]:
        """
        Récupère le mood actuel de l'utilisateur

        Args:
            user_id: ID de l'utilisateur

        Returns:
            Le mood de l'utilisateur ou None
        """
        cache_key = f"user_mood:{user_id}"
        mood_data = self.redis_client.get(cache_key)

        if mood_data and isinstance(mood_data, dict):
            return mood_data.get("mood")
        elif isinstance(mood_data, str):
            return mood_data

        return None

    async def set_user_mood(self, user_id: str, mood: str) -> bool:
        """
        Définit le mood de l'utilisateur

        Args:
            user_id: ID de l'utilisateur
            mood: Le mood à enregistrer

        Returns:
            True si l'enregistrement a réussi, False sinon
        """
        cache_key = f"user_mood:{user_id}"
        mood_data = {
            "mood": mood,
            "updated_at": datetime.now().isoformat()
        }
        return self.redis_client.set(cache_key, mood_data, self.USER_MOOD_TTL)

    async def get_daily_prayers(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Récupère les prières du jour (matin et soir) en cache

        Args:
            user_id: ID de l'utilisateur (optionnel, sinon prières globales)

        Returns:
            Dict contenant les prières du matin et du soir ou None
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"daily_prayers:{user_id or 'global'}:{today}"

        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        return None

    async def cache_daily_prayers(self, prayers_data: Dict[str, Any], user_id: str = None) -> bool:
        """
        Met en cache les prières du jour

        Args:
            prayers_data: Données des prières (matin et soir)
            user_id: ID de l'utilisateur (optionnel)

        Returns:
            True si le cache a réussi, False sinon
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"daily_prayers:{user_id or 'global'}:{today}"

        return self.redis_client.set(cache_key, prayers_data, self.DAILY_VERSE_TTL)

    async def get_morning_prayer(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Récupère la prière du matin en cache

        Args:
            user_id: ID de l'utilisateur (optionnel)

        Returns:
            Dict contenant la prière du matin ou None
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"morning_prayer:{user_id or 'global'}:{today}"

        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        return None

    async def cache_morning_prayer(self, prayer_data: Dict[str, Any], user_id: str = None) -> bool:
        """
        Met en cache la prière du matin

        Args:
            prayer_data: Données de la prière du matin
            user_id: ID de l'utilisateur (optionnel)

        Returns:
            True si le cache a réussi, False sinon
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"morning_prayer:{user_id or 'global'}:{today}"

        return self.redis_client.set(cache_key, prayer_data, self.DAILY_VERSE_TTL)

    async def get_evening_prayer(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Récupère la prière du soir en cache

        Args:
            user_id: ID de l'utilisateur (optionnel)

        Returns:
            Dict contenant la prière du soir ou None
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"evening_prayer:{user_id or 'global'}:{today}"

        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        return None

    async def cache_evening_prayer(self, prayer_data: Dict[str, Any], user_id: str = None) -> bool:
        """
        Met en cache la prière du soir

        Args:
            prayer_data: Données de la prière du soir
            user_id: ID de l'utilisateur (optionnel)

        Returns:
            True si le cache a réussi, False sinon
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"evening_prayer:{user_id or 'global'}:{today}"

        return self.redis_client.set(cache_key, prayer_data, self.DAILY_VERSE_TTL)
        cache_key = f"user_mood:{user_id}"
        mood_data = {
            "mood": mood,
            "declared_at": datetime.now().isoformat()
        }

        return self.redis_client.set(cache_key, mood_data, self.USER_MOOD_TTL)

    async def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les données utilisateur en cache

        Args:
            user_id: ID de l'utilisateur

        Returns:
            Dictionnaire des données utilisateur ou None
        """
        cache_key = f"user_data:{user_id}"
        return self.redis_client.get(cache_key)

    async def set_user_data(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """
        Met en cache les données utilisateur

        Args:
            user_id: ID de l'utilisateur
            user_data: Données utilisateur à cacher

        Returns:
            True si le cache a réussi, False sinon
        """
        cache_key = f"user_data:{user_id}"
        return self.redis_client.set(cache_key, user_data, self.USER_DATA_TTL)

    async def clear_user_cache(self, user_id: str) -> bool:
        """
        Supprime tout le cache lié à un utilisateur

        Args:
            user_id: ID de l'utilisateur

        Returns:
            True si la suppression a réussi, False sinon
        """
        pattern = f"*:{user_id}*"
        return self.redis_client.delete_pattern(pattern)

    async def get_verse_cache(self, translation: str, book: str, chapter: int, verse: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un verset spécifique en cache

        Args:
            translation: Traduction (ex: FreBBB)
            book: Livre de la Bible
            chapter: Chapitre
            verse: Numéro du verset

        Returns:
            Données du verset ou None
        """
        cache_key = f"verse:{translation}:{book}:{chapter}:{verse}"
        return self.redis_client.get(cache_key)

    async def cache_verse(self, translation: str, book: str, chapter: int, verse: int, verse_data: Dict[str, Any]) -> bool:
        """
        Met en cache un verset spécifique

        Args:
            translation: Traduction
            book: Livre
            chapter: Chapitre  
            verse: Numéro du verset
            verse_data: Données du verset

        Returns:
            True si le cache a réussi, False sinon
        """
        cache_key = f"verse:{translation}:{book}:{chapter}:{verse}"
        # 1 heure pour versets spécifiques
        return self.redis_client.set(cache_key, verse_data, 3600)

    async def invalidate_daily_verses(self, date: str = None) -> bool:
        """
        Invalide tous les versets quotidiens pour une date donnée

        Args:
            date: Date au format YYYY-MM-DD (par défaut aujourd'hui)

        Returns:
            True si l'invalidation a réussi, False sinon
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        pattern = f"daily_verse:*:{date}"
        return self.redis_client.delete_pattern(pattern)

    async def get_connection_status(self) -> bool:
        """
        Vérifie le statut de connexion à Redis

        Returns:
            True si connecté, False sinon
        """
        return self.redis_client.is_connected()
