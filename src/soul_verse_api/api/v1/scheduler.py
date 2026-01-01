# -*- coding: utf-8 -*-

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime
import logging

from src.soul_verse_api.services.scheduler_service import get_scheduler

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix='/scheduler', tags=['scheduler management'])
scheduler_service = get_scheduler()


@router.get("/status", response_model=Dict[str, Any])
async def get_scheduler_status():
    """Récupère le statut du planificateur"""
    try:
        status_data = scheduler_service.get_status()
        return status_data

    except Exception as e:
        logger.error(f"Erreur récupération statut scheduler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du statut"
        )


@router.post("/trigger-daily-verses", response_model=Dict[str, Any])
async def trigger_daily_verses():
    """Déclenche manuellement la génération des versets quotidiens"""
    try:
        result = await scheduler_service.trigger_daily_verses_manually()

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Erreur inconnue")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur déclenchement manuel versets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du déclenchement"
        )


@router.post("/test-morning-prayer", response_model=Dict[str, Any])
async def test_morning_prayer():
    """Déclenche manuellement la notification de prière du matin"""
    try:
        await scheduler_service._send_morning_prayer_job()
        return {
            "success": True,
            "message": "Notification de prière du matin envoyée",
            "triggered_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Erreur test prière matin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'envoi de la notification: {str(e)}"
        )


@router.post("/test-evening-prayer", response_model=Dict[str, Any])
async def test_evening_prayer():
    """Déclenche manuellement la notification de prière du soir"""
    try:
        await scheduler_service._send_evening_prayer_job()
        return {
            "success": True,
            "message": "Notification de prière du soir envoyée",
            "triggered_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Erreur test prière soir: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'envoi de la notification: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du déclenchement manuel"
        )


@router.post("/start")
async def start_scheduler():
    """Démarre le planificateur"""
    try:
        if scheduler_service.is_running:
            return {
                "message": "Planificateur déjà en cours d'exécution",
                "status": "already_running",
                "timestamp": datetime.now().isoformat()
            }

        scheduler_service.start()

        return {
            "message": "Planificateur démarré avec succès",
            "status": "started",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Erreur démarrage scheduler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du démarrage: {str(e)}"
        )


@router.post("/stop")
async def stop_scheduler():
    """Arrête le planificateur"""
    try:
        if not scheduler_service.is_running:
            return {
                "message": "Planificateur déjà arrêté",
                "status": "already_stopped",
                "timestamp": datetime.now().isoformat()
            }

        scheduler_service.stop()

        return {
            "message": "Planificateur arrêté avec succès",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Erreur arrêt scheduler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'arrêt: {str(e)}"
        )


@router.get("/users-count")
async def get_active_users_count():
    """Récupère le nombre d'utilisateurs actifs"""
    try:
        users = await scheduler_service.get_active_users()

        return {
            "total_active_users": len(users),
            "timestamp": datetime.now().isoformat(),
            "details": {
                "with_fcm_token": len([u for u in users if u.fcm_token]),
                "users_by_timezone": {}
            }
        }

    except Exception as e:
        logger.error(f"Erreur récupération nombre utilisateurs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du nombre d'utilisateurs"
        )


@router.post("/send-verse-to-all")
async def send_verse_to_all_users():
    """Endpoint de test - Envoie immédiatement un verset à tous les utilisateurs"""
    try:
        logger.info(
            "🚀 Déclenchement test - envoi verset à tous les utilisateurs")

        # Récupérer tous les utilisateurs actifs
        users = await scheduler_service.get_active_users()

        if not users:
            return {
                "success": False,
                "message": "Aucun utilisateur actif trouvé",
                "total_users": 0,
                "timestamp": datetime.now().isoformat()
            }

        # Statistiques de traitement
        total_users = len(users)
        success_count = 0
        error_count = 0
        results = []

        logger.info(f"📨 Traitement de {total_users} utilisateurs...")

        # Traiter tous les utilisateurs
        for user in users:
            try:
                user_id = str(user.id)

                # Générer un verset test pour cet utilisateur
                verse_result = await scheduler_service._generate_user_daily_verse(user)

                if verse_result:
                    success_count += 1
                    results.append({
                        "user_id": user_id[:8] + "...",  # Masquer l'ID complet
                        "status": "success",
                        "mood": user.mood or "paix"
                    })
                else:
                    error_count += 1
                    results.append({
                        "user_id": user_id[:8] + "...",
                        "status": "error",
                        "reason": "Échec génération verset"
                    })

            except Exception as e:
                error_count += 1
                results.append({
                    "user_id": str(user.id)[:8] + "...",
                    "status": "error",
                    "reason": str(e)
                })
                logger.error(f"Erreur traitement utilisateur {user.id}: {e}")

        # Résultat final
        success_rate = (success_count / total_users *
                        100) if total_users > 0 else 0

        response = {
            "success": True,
            "message": f"Test terminé - {success_count}/{total_users} utilisateurs traités avec succès",
            "statistics": {
                "total_users": total_users,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate_percent": round(success_rate, 2)
            },
            # Limiter à 10 premiers résultats pour éviter réponse trop large
            "results": results[:10],
            "note": "Les versets ont été mis en cache Redis et sont disponibles via /api/v1/verses/today",
            "timestamp": datetime.now().isoformat()
        }

        logger.info(
            f"✅ Test terminé: {success_count} succès, {error_count} erreurs ({success_rate:.1f}%)")
        return response

    except Exception as e:
        logger.error(f"Erreur critique dans envoi test versets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'envoi test: {str(e)}"
        )


@router.post("/send-custom-verse-to-all")
async def send_custom_verse_to_all(mood: str = "paix", translation: str = "FreBBB"):
    """Endpoint de test - Envoie un verset personnalisé à tous les utilisateurs avec un mood spécifique"""
    try:
        logger.info(
            f"🎯 Test verset personnalisé - mood: {mood}, traduction: {translation}")

        # Valider le mood
        valid_moods = ["paix", "joie", "tristesse", "anxiété", "gratitude",
                       "espoir", "doute", "colère", "amour", "peur", "fatigue"]
        if mood not in valid_moods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mood invalide. Moods valides: {', '.join(valid_moods)}"
            )

        # Récupérer utilisateurs actifs
        users = await scheduler_service.get_active_users()

        if not users:
            return {
                "success": False,
                "message": "Aucun utilisateur actif trouvé",
                "timestamp": datetime.now().isoformat()
            }

        # Générer UN verset pour le mood spécifié (économie d'appels IA)
        from src.soul_verse_api.services.gemini_service import GeminiService
        gemini_service = GeminiService()

        try:
            ai_response = await gemini_service.get_personalized_verse(mood)
        except Exception as e:
            logger.warning(f"Erreur IA, utilisation fallback: {e}")
            # Utiliser fallback
            ai_response = await scheduler_service._get_fallback_verse(mood)

        # Appliquer ce verset à tous les utilisateurs
        success_count = 0
        error_count = 0

        # Récupérer le texte complet du verset depuis la Bible
        bible_verse = await scheduler_service.get_bible_verse_from_reference(
            ai_response.get("reference", ""),
            translation
        )

        # Générer l'image une seule fois pour tous les utilisateurs (économie)
        verse_image = None
        try:
            from src.soul_verse_api.services.image_generation_service import get_image_service
            image_service = get_image_service()

            # Utiliser le texte du verset si disponible, sinon la réflexion
            verse_text = bible_verse.text if bible_verse else ai_response.get("reflection", "")[
                :100] + "..."

            verse_image = await image_service.generate_multiple_methods(
                verse_text=verse_text,
                reference=ai_response.get("reference", "Verset du jour"),
                mood=mood
            )
            logger.info(
                f"✅ Image générée pour mood {mood}: {verse_image.get('method', 'unknown')}")
        except Exception as e:
            logger.warning(f"⚠️ Erreur génération image commune: {e}")

        for user in users:
            try:
                user_id = str(user.id)

                # Construire les données du verset avec le verset complet de la Bible
                verse_data = {
                    "verse": bible_verse.dict() if bible_verse else None,
                    "ai_response": ai_response,
                    "ai_reflection": ai_response.get("reflection", ""),
                    "verse_image": verse_image,
                    "mood_context": mood,
                    "reference": ai_response.get("reference", "Verset personnalisé"),
                    "generated_at": datetime.now().isoformat(),
                    "user_id": user_id,
                    "translation": translation,
                    "test_mode": True,
                    "custom_mood": True,
                    "has_full_verse": bible_verse is not None,
                    "has_image": verse_image is not None and verse_image.get("image_url") != "/static/default_verse.png"
                }

                # Mettre en cache
                cache_success = await scheduler_service.redis_service.cache_daily_verse(user_id, verse_data)

                if cache_success:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Erreur cache utilisateur {user.id}: {e}")

        return {
            "success": True,
            "message": f"Verset personnalisé envoyé avec succès",
            "verse_reference": ai_response.get("reference", "Référence non disponible"),
            "verse_found_in_bible": bible_verse is not None,
            "mood_used": mood,
            "translation_used": translation,
            "statistics": {
                "total_users": len(users),
                "success_count": success_count,
                "error_count": error_count,
                "success_rate_percent": round((success_count / len(users) * 100), 2)
            },
            "note": "Tous les utilisateurs ont reçu le même verset basé sur le mood spécifié avec texte complet de la Bible si disponible",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans envoi verset personnalisé: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'envoi personnalisé: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Vérifie l'état de santé du service scheduler"""
    try:
        scheduler_status = scheduler_service.get_status()

        return {
            "service": "scheduler",
            "status": "healthy" if scheduler_status["running"] else "degraded",
            "scheduler_running": scheduler_status["running"],
            "jobs_count": scheduler_status["jobs_count"],
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }

    except Exception as e:
        logger.error(f"Erreur health check scheduler: {e}")
        return {
            "service": "scheduler",
            "status": "unhealthy",
            "scheduler_running": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
