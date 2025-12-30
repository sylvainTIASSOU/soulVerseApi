# -*- coding: utf-8 -*-

import json
from typing import Any, Optional

import redis
from redis import Redis

from src.soul_verse_api.core.config import settings


class RedisClient:
    """Client Redis pour la gestion du cache"""

    def __init__(self):
        self._redis: Optional[Redis] = None

    def connect(self):
        """Établir la connexion à Redis"""
        try:
            self._redis = redis.from_url(
                settings.REDIS_HOST,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # Test de connexion
            self._redis.ping()
            print("✅ Connexion à Redis établie avec succès")
        except Exception as e:
            print(f"⚠️ Impossible de se connecter à Redis: {e}")
            self._redis = None

    def disconnect(self):
        """Fermer la connexion à Redis"""
        if self._redis:
            self._redis.close()
            print("✅ Connexion à Redis fermée")

    def get(self, key: str) -> Optional[Any]:
        """
        Récupérer une valeur depuis Redis
        
        Args:
            key: Clé du cache
            
        Returns:
            La valeur désérialisée ou None si la clé n'existe pas
        """
        if not self._redis:
            return None

        try:
            value = self._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération du cache Redis: {e}")
            return None

    def set(self, key: str, value: Any, expire: int = 300) -> bool:
        """
        Stocker une valeur dans Redis
        
        Args:
            key: Clé du cache
            value: Valeur à stocker (sera sérialisée en JSON)
            expire: Durée de vie en secondes (par défaut 5 minutes)
            
        Returns:
            True si le stockage a réussi, False sinon
        """
        if not self._redis:
            return False

        try:
            serialized_value = json.dumps(
                value, ensure_ascii=False, default=str)
            self._redis.setex(key, expire, serialized_value)
            return True
        except Exception as e:
            print(f"⚠️ Erreur lors du stockage dans Redis: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Supprimer une clé du cache
        
        Args:
            key: Clé à supprimer
            
        Returns:
            True si la suppression a réussi, False sinon
        """
        if not self._redis:
            return False

        try:
            self._redis.delete(key)
            return True
        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression du cache Redis: {e}")
            return False

    def delete_pattern(self, pattern: str) -> bool:
        """
        Supprimer toutes les clés correspondant à un pattern
        
        Args:
            pattern: Pattern de clés (ex: "categories:*")
            
        Returns:
            True si la suppression a réussi, False sinon
        """
        if not self._redis:
            return False

        try:
            keys = self._redis.keys(pattern)
            if keys:
                self._redis.delete(*keys)
            return True
        except Exception as e:
            print(
                f"⚠️ Erreur lors de la suppression par pattern dans Redis: {e}")
            return False

    def is_connected(self) -> bool:
        """Vérifier si Redis est connecté"""
        if not self._redis:
            return False
        try:
            self._redis.ping()
            return True
        except Exception:
            return False


# Instance globale du client Redis
redis_client = RedisClient()


def get_redis() -> RedisClient:
    """Dependency pour obtenir le client Redis"""
    return redis_client
