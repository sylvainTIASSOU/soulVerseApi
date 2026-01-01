from fastapi import APIRouter, HTTPException, status
from src.soul_verse_api.services.bible_service import BibleService
from src.soul_verse_api.services.gemini_service import GeminiService
from src.soul_verse_api.services.redis_service import RedisService
from src.soul_verse_api.services.image_generation_service import get_image_service
from src.soul_verse_api.services.scheduler_service import get_scheduler
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter(prefix='/verses', tags=['verses management'])
bible_service = BibleService()
gemini_service = GeminiService()
redis_service = RedisService()
image_service = get_image_service()
scheduler_service = get_scheduler()


@router.get("/today", response_model=Dict[str, Any])
async def get_daily_verse(user_id: str):
    """Récupère le verset du jour personnalisé (avec IA)"""
    try:
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'ID utilisateur est requis"
            )

        # Vérifier cache Redis d'abord
        cached_verse = await redis_service.get_daily_verse(user_id)
        if cached_verse:
            # Vérifier si le cache contient un verset complet
            if cached_verse.get("verse") is not None and cached_verse.get("has_full_verse") is True:
                logger.info(
                    f"✅ Verset quotidien complet trouvé en cache pour l'utilisateur {user_id[:8]}...")
                return cached_verse
            else:
                logger.warning(
                    f"⚠️ Cache incomplet pour {user_id[:8]}... (verse=null), régénération nécessaire")
                # Invalider le cache incomplet
                await redis_service.delete_daily_verse(user_id)

        # Récupérer mood utilisateur
        mood = await redis_service.get_user_mood(user_id) or "paix"
        logger.info(f"Mood utilisateur {user_id}: {mood}")

        # Générer verset avec IA
        try:
            ai_response = await gemini_service.get_personalized_verse(mood)
        except Exception as e:
            logger.error(f"Erreur lors de la génération IA: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service IA temporairement indisponible"
            )

        # Valider la réponse IA
        if not ai_response or "reference" not in ai_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Réponse IA invalide"
            )

        # Récupérer le verset complet depuis la Bible en utilisant la fonction utilitaire
        bible_verse = await scheduler_service.get_bible_verse_from_reference(
            ai_response["reference"],
            "FreBBB"
        )

        if not bible_verse:
            logger.warning(
                f"⚠️ Verset non trouvé pour référence: {ai_response['reference']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verset non trouvé: {ai_response['reference']}"
            )

        # Générer l'image du verset
        verse_image = None
        try:
            logger.info(
                f"Génération image pour verset: {ai_response['reference']}")
            verse_image = await image_service.generate_multiple_methods(
                verse_text=bible_verse.text,
                reference=ai_response["reference"],
                mood=mood
            )
        except Exception as e:
            logger.warning(f"Erreur génération image: {e}")
            # Continue sans image si la génération échoue

        # Construire réponse enrichie
        result = {
            "verse": bible_verse.dict() if hasattr(bible_verse, 'dict') else bible_verse,
            "ai_response": ai_response,
            "ai_reflection": ai_response.get("reflection", "Méditation personnalisée indisponible"),
            "verse_image": verse_image,
            "mood_context": mood,
            "generated_at": datetime.now().isoformat(),
            "reference": ai_response["reference"],
            "user_id": user_id,
            "translation": "FreBBB",
            "has_full_verse": True,
            "has_image": verse_image is not None and verse_image.get("image_url") != "/static/default_verse.png"
        }

        # Mettre en cache Redis (async)
        try:
            await redis_service.cache_daily_verse(user_id, result)
            logger.info(
                f"Verset quotidien mis en cache pour l'utilisateur {user_id}")
        except Exception as e:
            logger.warning(
                f"Impossible de mettre en cache le verset pour {user_id}: {e}")
            # Continue sans échec si le cache ne fonctionne pas

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue dans get_daily_verse: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.delete("/today/cache", response_model=Dict[str, Any])
async def clear_daily_verse_cache(user_id: str):
    """Supprime le cache du verset quotidien pour un utilisateur (utile pour forcer la régénération)"""
    try:
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'ID utilisateur est requis"
            )

        # Supprimer le cache
        deleted = await redis_service.delete_daily_verse(user_id)

        if deleted:
            logger.info(
                f"✅ Cache supprimé pour l'utilisateur {user_id[:8]}...")
            return {
                "success": True,
                "message": "Cache du verset quotidien supprimé",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Aucun cache à supprimer ou erreur lors de la suppression",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Erreur lors de la suppression du cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )


@router.get("/{book}/{chapter}/{verse}", response_model=Dict[str, Any])
async def get_specific_verse(
    book: str,
    chapter: int,
    verse: int,
    translation: str = "FreBBB"
):
    """Récupère un verset spécifique avec cache optimisé"""
    try:
        # Validation des paramètres
        if not book or not book.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nom du livre est requis"
            )

        if chapter <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le numéro de chapitre doit être positif"
            )

        if verse <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le numéro de verset doit être positif"
            )

        # Nettoyer les paramètres
        book = book.strip()
        translation = translation.strip() or "FreBBB"

        # Vérifier cache Redis d'abord
        try:
            cached_verse = await redis_service.get_verse_cache(translation, book, chapter, verse)
            if cached_verse:
                logger.info(
                    f"Verset trouvé en cache: {book} {chapter}:{verse} ({translation})")
                return cached_verse
        except Exception as e:
            logger.warning(f"Erreur cache Redis: {e}")
            # Continue sans cache si Redis ne fonctionne pas

        # Récupérer depuis le service Bible
        try:
            bible_verse = await bible_service.get_verse(translation, book, chapter, verse)
        except Exception as e:
            logger.error(f"Erreur service Bible: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service Bible temporairement indisponible"
            )

        if not bible_verse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verset non trouvé: {book} {chapter}:{verse} ({translation})"
            )

        # Préparer la réponse
        if hasattr(bible_verse, 'dict'):
            result = bible_verse.dict()
        else:
            result = bible_verse

        # Ajouter métadonnées
        result.update({
            "retrieved_at": datetime.now().isoformat(),
            "translation": translation,
            "reference": f"{book} {chapter}:{verse}"
        })

        # Mettre en cache (async, non bloquant)
        try:
            await redis_service.cache_verse(translation, book, chapter, verse, result)
            logger.info(
                f"Verset mis en cache: {book} {chapter}:{verse} ({translation})")
        except Exception as e:
            logger.warning(f"Impossible de mettre en cache: {e}")
            # Continue sans échec si le cache ne fonctionne pas

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue dans get_specific_verse: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.post("/mood")
async def set_user_mood(user_id: str, mood: str):
    """Définit le mood de l'utilisateur pour personnaliser les versets"""
    try:
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'ID utilisateur est requis"
            )

        if not mood or not mood.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le mood est requis"
            )

        mood = mood.strip().lower()

        # Valider le mood (optionnel - liste prédéfinie)
        valid_moods = [
            "joie", "paix", "tristesse", "anxiété", "gratitude",
            "espoir", "doute", "colère", "amour", "peur", "fatigue",
            "reconnaissance", "pardon", "force", "patience"
        ]

        if mood not in valid_moods:
            logger.warning(f"Mood non standard utilisé: {mood}")

        # Enregistrer le mood
        success = await redis_service.set_user_mood(user_id, mood)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Impossible d'enregistrer le mood"
            )

        logger.info(f"Mood '{mood}' enregistré pour l'utilisateur {user_id}")

        return {
            "message": f"Mood '{mood}' enregistré avec succès",
            "user_id": user_id,
            "mood": mood,
            "recorded_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du mood: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.get("/mood/{user_id}")
async def get_user_mood(user_id: str):
    """Récupère le mood actuel de l'utilisateur"""
    try:
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'ID utilisateur est requis"
            )

        mood = await redis_service.get_user_mood(user_id)

        if not mood:
            return {
                "user_id": user_id,
                "mood": None,
                "message": "Aucun mood enregistré pour cet utilisateur"
            }

        return {
            "user_id": user_id,
            "mood": mood,
            "retrieved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du mood: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.delete("/cache/{user_id}")
async def clear_user_cache(user_id: str):
    """Supprime tout le cache d'un utilisateur"""
    try:
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'ID utilisateur est requis"
            )

        success = await redis_service.clear_user_cache(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Impossible de vider le cache"
            )

        logger.info(f"Cache vidé pour l'utilisateur {user_id}")

        return {
            "message": f"Cache vidé avec succès pour l'utilisateur {user_id}",
            "user_id": user_id,
            "cleared_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du vidage du cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.get("/health")
async def health_check():
    """Vérifie l'état de santé du service versets"""
    try:
        redis_status = await redis_service.get_connection_status()

        return {
            "service": "verses",
            "status": "healthy" if redis_status else "degraded",
            "redis_connected": redis_status,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }

    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return {
            "service": "verses",
            "status": "unhealthy",
            "redis_connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/generate-image")
async def generate_verse_image(
    verse_text: str,
    reference: str,
    mood: str = "paix",
    method: str = "auto"
):
    """Génère une image pour un verset spécifique"""
    try:
        # Valider les paramètres
        if not verse_text or not verse_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le texte du verset est requis"
            )

        if not reference or not reference.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La référence est requise"
            )

        # Valider la méthode
        valid_methods = ["auto", "local", "dalle", "stability"]
        if method not in valid_methods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Méthode invalide. Méthodes valides: {', '.join(valid_methods)}"
            )

        # Générer l'image
        if method == "auto":
            image_result = await image_service.generate_multiple_methods(
                verse_text=verse_text.strip(),
                reference=reference.strip(),
                mood=mood.strip()
            )
        else:
            image_result = await image_service.generate_verse_image(
                verse_text=verse_text.strip(),
                reference=reference.strip(),
                mood=mood.strip(),
                method=method
            )

        if not image_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Échec de la génération d'image"
            )

        return {
            "success": True,
            "image": image_result,
            "verse_text": verse_text,
            "reference": reference,
            "mood": mood,
            "method_used": image_result.get("method", "unknown"),
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur génération image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération d'image: {str(e)}"
        )


@router.get("/image-status")
async def get_image_service_status():
    """Vérifie le statut du service de génération d'images"""
    try:
        return {
            "service": "image_generation",
            "status": "healthy",
            "available_methods": {
                "local": True,
                # Temporairement désactivé (API non disponible)
                "gemini": False,
                "dalle": image_service.openai_api_key is not None,
                "stability": image_service.stability_api_key is not None
            },
            "storage_directory": str(image_service.local_images_dir),
            "color_themes_available": list(image_service.color_themes.keys()),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Erreur status service image: {e}")
        return {
            "service": "image_generation",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
