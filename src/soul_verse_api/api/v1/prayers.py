# -*- coding: utf-8 -*-

from fastapi import APIRouter, HTTPException, status
from src.soul_verse_api.services.redis_service import RedisService
from src.soul_verse_api.services.gemini_service import GeminiService
from src.soul_verse_api.services.scheduler_service import get_scheduler
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix='/prayers', tags=['prayers management'])
redis_service = RedisService()
gemini_service = GeminiService()
scheduler_service = get_scheduler()


@router.get("/daily", response_model=Dict[str, Any])
async def get_daily_prayers(user_id: Optional[str] = None):
    """
    Récupère les prières du jour (matin et soir) personnalisées

    Args:
        user_id: ID utilisateur (optionnel) - si fourni, peut être personnalisé selon le mood

    Returns:
        {
            "morning_prayer": {...},
            "evening_prayer": {...},
            "special_occasion": {...},
            "retrieved_at": "..."
        }
    """
    try:
        logger.info(
            f"📿 Récupération des prières du jour{f' pour utilisateur {user_id[:8]}...' if user_id else ' (globales)'}")

        # Détecter l'occasion spéciale du jour
        special_occasion = scheduler_service.get_special_occasion()

        # Vérifier cache d'abord
        cached_morning = await redis_service.get_morning_prayer(user_id)
        cached_evening = await redis_service.get_evening_prayer(user_id)

        # Si les deux sont en cache, retourner
        if cached_morning and cached_evening:
            logger.info("✅ Prières trouvées en cache")
            return {
                "morning_prayer": cached_morning,
                "evening_prayer": cached_evening,
                "special_occasion": {
                    "name": special_occasion.get("name") if special_occasion else None,
                    "description": special_occasion.get("description") if special_occasion else None,
                    "priority": special_occasion.get("priority") if special_occasion else None
                } if special_occasion else None,
                "retrieved_at": datetime.now().isoformat(),
                "cached": True
            }

        # Générer les prières si pas en cache
        mood = "paix"  # Par défaut
        if user_id:
            user_mood = await redis_service.get_user_mood(user_id)
            if user_mood:
                mood = user_mood

        # Générer prière du matin si nécessaire
        if not cached_morning:
            logger.info("🌅 Génération prière du matin...")
            try:
                morning_prayer = await gemini_service.generate_morning_prayer(mood, special_occasion)
            except Exception as e:
                logger.warning(f"Erreur génération prière matin: {e}")
                morning_prayer = await gemini_service._get_fallback_morning_prayer(mood, special_occasion)

            morning_data = {
                "prayer_title": morning_prayer.get("prayer_title", "Prière du Matin"),
                "prayer_text": morning_prayer.get("prayer_text", ""),
                "blessing": morning_prayer.get("blessing", "Que Dieu te bénisse. Amen."),
                "suggested_verse": morning_prayer.get("suggested_verse", ""),
                "special_occasion": special_occasion.get("name") if special_occasion else None,
                "occasion_description": special_occasion.get("description") if special_occasion else None,
                "generated_at": datetime.now().isoformat(),
                "prayer_type": "morning"
            }

            # Mettre en cache
            await redis_service.cache_morning_prayer(morning_data, user_id)
            cached_morning = morning_data

        # Générer prière du soir si nécessaire
        if not cached_evening:
            logger.info("🌙 Génération prière du soir...")
            try:
                evening_prayer = await gemini_service.generate_evening_prayer(mood, special_occasion)
            except Exception as e:
                logger.warning(f"Erreur génération prière soir: {e}")
                evening_prayer = await gemini_service._get_fallback_evening_prayer(mood, special_occasion)

            evening_data = {
                "prayer_title": evening_prayer.get("prayer_title", "Prière du Soir"),
                "prayer_text": evening_prayer.get("prayer_text", ""),
                "blessing": evening_prayer.get("blessing", "Que tu reposes en paix. Amen."),
                "suggested_verse": evening_prayer.get("suggested_verse", ""),
                "special_occasion": special_occasion.get("name") if special_occasion else None,
                "occasion_description": special_occasion.get("description") if special_occasion else None,
                "generated_at": datetime.now().isoformat(),
                "prayer_type": "evening"
            }

            # Mettre en cache
            await redis_service.cache_evening_prayer(evening_data, user_id)
            cached_evening = evening_data

        return {
            "morning_prayer": cached_morning,
            "evening_prayer": cached_evening,
            "special_occasion": {
                "name": special_occasion.get("name") if special_occasion else None,
                "description": special_occasion.get("description") if special_occasion else None,
                "priority": special_occasion.get("priority") if special_occasion else None,
                "themes": special_occasion.get("themes") if special_occasion else None
            } if special_occasion else None,
            "retrieved_at": datetime.now().isoformat(),
            "cached": False,
            "generated_for_user": user_id is not None,
            "mood_context": mood if user_id else "paix"
        }

    except Exception as e:
        logger.error(f"❌ Erreur récupération prières: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des prières: {str(e)}"
        )


@router.get("/morning", response_model=Dict[str, Any])
async def get_morning_prayer(user_id: Optional[str] = None):
    """
    Récupère uniquement la prière du matin

    Args:
        user_id: ID utilisateur (optionnel)

    Returns:
        Données de la prière du matin
    """
    try:
        logger.info(
            f"🌅 Récupération prière du matin{f' pour {user_id[:8]}...' if user_id else ''}")

        # Vérifier cache
        cached = await redis_service.get_morning_prayer(user_id)
        if cached:
            return cached

        # Générer si pas en cache
        special_occasion = scheduler_service.get_special_occasion()
        mood = "paix"
        if user_id:
            user_mood = await redis_service.get_user_mood(user_id)
            if user_mood:
                mood = user_mood

        try:
            prayer = await gemini_service.generate_morning_prayer(mood, special_occasion)
        except Exception as e:
            logger.warning(f"Erreur IA: {e}")
            prayer = await gemini_service._get_fallback_morning_prayer(mood, special_occasion)

        prayer_data = {
            "prayer_title": prayer.get("prayer_title", "Prière du Matin"),
            "prayer_text": prayer.get("prayer_text", ""),
            "blessing": prayer.get("blessing", ""),
            "suggested_verse": prayer.get("suggested_verse", ""),
            "special_occasion": special_occasion.get("name") if special_occasion else None,
            "generated_at": datetime.now().isoformat(),
            "prayer_type": "morning"
        }

        await redis_service.cache_morning_prayer(prayer_data, user_id)
        return prayer_data

    except Exception as e:
        logger.error(f"Erreur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/evening", response_model=Dict[str, Any])
async def get_evening_prayer(user_id: Optional[str] = None):
    """
    Récupère uniquement la prière du soir

    Args:
        user_id: ID utilisateur (optionnel)

    Returns:
        Données de la prière du soir
    """
    try:
        logger.info(
            f"🌙 Récupération prière du soir{f' pour {user_id[:8]}...' if user_id else ''}")

        # Vérifier cache
        cached = await redis_service.get_evening_prayer(user_id)
        if cached:
            return cached

        # Générer si pas en cache
        special_occasion = scheduler_service.get_special_occasion()
        mood = "paix"
        if user_id:
            user_mood = await redis_service.get_user_mood(user_id)
            if user_mood:
                mood = user_mood

        try:
            prayer = await gemini_service.generate_evening_prayer(mood, special_occasion)
        except Exception as e:
            logger.warning(f"Erreur IA: {e}")
            prayer = await gemini_service._get_fallback_evening_prayer(mood, special_occasion)

        prayer_data = {
            "prayer_title": prayer.get("prayer_title", "Prière du Soir"),
            "prayer_text": prayer.get("prayer_text", ""),
            "blessing": prayer.get("blessing", ""),
            "suggested_verse": prayer.get("suggested_verse", ""),
            "special_occasion": special_occasion.get("name") if special_occasion else None,
            "generated_at": datetime.now().isoformat(),
            "prayer_type": "evening"
        }

        await redis_service.cache_evening_prayer(prayer_data, user_id)
        return prayer_data

    except Exception as e:
        logger.error(f"Erreur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/generate-custom", response_model=Dict[str, Any])
async def generate_custom_prayer(
    prayer_type: str,  # "morning" ou "evening"
    mood: str = "paix",
    user_id: Optional[str] = None
):
    """
    Génère une prière personnalisée à la demande

    Args:
        prayer_type: Type de prière ("morning" ou "evening")
        mood: État émotionnel
        user_id: ID utilisateur (optionnel)

    Returns:
        Prière générée
    """
    try:
        if prayer_type not in ["morning", "evening"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="prayer_type doit être 'morning' ou 'evening'"
            )

        special_occasion = scheduler_service.get_special_occasion()

        if prayer_type == "morning":
            prayer = await gemini_service.generate_morning_prayer(mood, special_occasion)
        else:
            prayer = await gemini_service.generate_evening_prayer(mood, special_occasion)

        return {
            **prayer,
            "prayer_type": prayer_type,
            "mood": mood,
            "special_occasion": special_occasion.get("name") if special_occasion else None,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Erreur génération prière custom: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
