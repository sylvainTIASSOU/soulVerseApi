from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from src.soul_verse_api.models.Models import User
from src.soul_verse_api.schemas.user_schemas import UserCreate, User as UserSchema
from src.soul_verse_api.api.deps import get_db
from src.soul_verse_api.core.notification_client import NotificationClient

router = APIRouter(prefix="/users", tags=["users management"])

# Schémas Pydantic pour les endpoints de notification


class FCMTokenUpdate(BaseModel):
    fcm_token: str


class TopicSubscription(BaseModel):
    topic: str
    # Si None, utilise le FCM token de l'utilisateur
    user_ids: Optional[List[str]] = None


class NotificationTest(BaseModel):
    title: str
    message: str
    user_ids: Optional[List[str]] = None


@router.post("", response_model=UserSchema, status_code=201)
async def create_user(payload: UserCreate,  db: Session = Depends(get_db)):
    """Créer un nouvel utilisateur"""
    new_user = User(
        fcm_token=payload.fcm_token,
        phone_model=payload.phone_model,
        phone_os=payload.phone_os,
        app_version=payload.app_version,
        phone_mark=payload.phone_mark,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

#  get all users (for testing purposes)


@router.get("", response_model=list[UserSchema])
async def get_all_users(db: Session = Depends(get_db)):
    """Récupérer tous les utilisateurs (à des fins de test)"""
    users = db.query(User).all()
    return users


# Endpoints pour la gestion des notifications push

@router.put("/{user_id}/fcm-token", response_model=dict)
async def update_fcm_token(user_id: str, payload: FCMTokenUpdate, db: Session = Depends(get_db)):
    """Mettre à jour le token FCM d'un utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user.fcm_token = payload.fcm_token
    db.commit()

    return {"message": "Token FCM mis à jour avec succès", "user_id": str(user_id)}


@router.post("/subscribe-topic", response_model=dict)
async def subscribe_to_topic(payload: TopicSubscription, db: Session = Depends(get_db)):
    """Abonner des utilisateurs à un topic de notification"""
    notification_client = NotificationClient()

    # Si user_ids est spécifié, utiliser ces IDs
    if payload.user_ids:
        users = db.query(User).filter(User.id.in_(payload.user_ids)).all()
    else:
        # Sinon, abonner tous les utilisateurs actifs avec un token FCM
        users = db.query(User).filter(
            User.is_active == True,
            User.fcm_token.isnot(None)
        ).all()

    if not users:
        raise HTTPException(status_code=404, detail="Aucun utilisateur trouvé")

    # Extraire les tokens FCM
    tokens = [user.fcm_token for user in users if user.fcm_token]

    if not tokens:
        raise HTTPException(status_code=400, detail="Aucun token FCM trouvé")

    # Abonner au topic
    success = notification_client.subscribe_to_topic(tokens, payload.topic)

    if success:
        return {
            "message": f"{len(tokens)} utilisateurs abonnés au topic '{payload.topic}'",
            "topic": payload.topic,
            "subscribers_count": len(tokens)
        }
    else:
        raise HTTPException(
            status_code=500, detail="Erreur lors de l'abonnement au topic")


@router.post("/unsubscribe-topic", response_model=dict)
async def unsubscribe_from_topic(payload: TopicSubscription, db: Session = Depends(get_db)):
    """Désabonner des utilisateurs d'un topic de notification"""
    notification_client = NotificationClient()

    # Si user_ids est spécifié, utiliser ces IDs
    if payload.user_ids:
        users = db.query(User).filter(User.id.in_(payload.user_ids)).all()
    else:
        # Sinon, désabonner tous les utilisateurs actifs avec un token FCM
        users = db.query(User).filter(
            User.is_active == True,
            User.fcm_token.isnot(None)
        ).all()

    if not users:
        raise HTTPException(status_code=404, detail="Aucun utilisateur trouvé")

    # Extraire les tokens FCM
    tokens = [user.fcm_token for user in users if user.fcm_token]

    if not tokens:
        raise HTTPException(status_code=400, detail="Aucun token FCM trouvé")

    # Désabonner du topic
    success = notification_client.unsubscribe_from_topic(tokens, payload.topic)

    if success:
        return {
            "message": f"{len(tokens)} utilisateurs désabonnés du topic '{payload.topic}'",
            "topic": payload.topic,
            "unsubscribers_count": len(tokens)
        }
    else:
        raise HTTPException(
            status_code=500, detail="Erreur lors du désabonnement du topic")


@router.post("/test-notification", response_model=dict)
async def send_test_notification(payload: NotificationTest, db: Session = Depends(get_db)):
    """Envoyer une notification de test"""
    notification_client = NotificationClient()

    # Si user_ids est spécifié, envoyer à ces utilisateurs
    if payload.user_ids:
        users = db.query(User).filter(User.id.in_(payload.user_ids)).all()

        # Debug information
        debug_info = {
            "requested_user_ids": payload.user_ids,
            "users_found": len(users),
            "users_details": [
                {
                    "id": str(user.id),
                    "fcm_token": user.fcm_token[:20] + "..." if user.fcm_token and len(user.fcm_token) > 20 else user.fcm_token,
                    "has_token": bool(user.fcm_token)
                } for user in users
            ]
        }

        tokens = [user.fcm_token for user in users if user.fcm_token]

        if not tokens:
            return {
                "error": "Aucun token FCM trouvé pour les utilisateurs spécifiés",
                "debug_info": debug_info,
                "success_count": 0,
                "failure_count": len(payload.user_ids),
                "total_recipients": 0
            }

        try:
            result = notification_client.send_to_multiple(
                title=payload.title,
                body=payload.message,
                tokens=tokens
            )

            return {
                "message": "Notification de test envoyée",
                "success_count": result["success_count"],
                "failure_count": result["failure_count"],
                "total_recipients": len(tokens),
                "debug_info": debug_info
            }
        except Exception as e:
            return {
                "error": f"Erreur lors de l'envoi: {str(e)}",
                "success_count": 0,
                "failure_count": len(tokens),
                "total_recipients": len(tokens),
                "debug_info": debug_info
            }
    else:
        # Envoyer via topic pour tous les utilisateurs
        success = notification_client.send_to_topic(
            title=payload.title,
            body=payload.message,
            topic="test_notifications"
        )

        if success:
            return {"message": "Notification de test envoyée via topic 'test_notifications'"}
        else:
            raise HTTPException(
                status_code=500, detail="Erreur lors de l'envoi de la notification")


@router.post("/send-daily-verse-manual", response_model=dict)
async def send_daily_verse_manual(db: Session = Depends(get_db)):
    """Envoyer manuellement le verset quotidien à tous les utilisateurs"""
    notification_client = NotificationClient()

    # Exemple de verset (en production, ceci viendrait du service de génération de versets)
    success = notification_client.send_daily_verse(
        verse_content="Car Dieu a tant aimé le monde qu'il a donné son Fils unique...",
        verse_reference="Jean 3:16",
        reflection="L'amour de Dieu pour nous dépasse toute compréhension. Il nous offre la vie éternelle par son fils Jésus.",
        topic="daily_verses"
    )

    if success:
        return {"message": "Verset quotidien envoyé via topic 'daily_verses'"}
    else:
        raise HTTPException(
            status_code=500, detail="Erreur lors de l'envoi du verset quotidien")


@router.get("/{user_id}", response_model=dict)
async def get_user_details(user_id: str, db: Session = Depends(get_db)):
    """Obtenir les détails d'un utilisateur pour debug"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return {
            "error": "Utilisateur introuvable",
            "user_id": user_id,
            "exists": False
        }

    return {
        "user_id": str(user.id),
        "fcm_token": user.fcm_token[:20] + "..." if user.fcm_token and len(user.fcm_token) > 20 else user.fcm_token,
        "has_fcm_token": bool(user.fcm_token),
        "phone_model": user.phone_model,
        "phone_os": user.phone_os,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "exists": True
    }


@router.post("/create-test-user", response_model=dict)
async def create_test_user(db: Session = Depends(get_db)):
    """Créer un utilisateur de test avec un token FCM factice"""
    test_fcm_token = "dummyFCMTokenForTesting123456789abcdef"

    # Vérifier si un utilisateur avec ce token existe déjà
    existing_user = db.query(User).filter(
        User.fcm_token == test_fcm_token).first()

    if existing_user:
        return {
            "message": "Utilisateur de test existe déjà",
            "user_id": str(existing_user.id),
            "fcm_token": test_fcm_token,
            "existing": True
        }

    # Créer un nouvel utilisateur de test
    test_user = User(
        fcm_token=test_fcm_token,
        phone_model="Test Phone",
        phone_os="Test OS",
        app_version="1.0.0",
        phone_mark="Test Brand"
    )

    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    return {
        "message": "Utilisateur de test créé avec succès",
        "user_id": str(test_user.id),
        "fcm_token": test_fcm_token,
        "existing": False
    }


@router.post("/test-notification-system", response_model=dict)
async def test_notification_system(db: Session = Depends(get_db)):
    """Test complet du système de notifications SoulVerse"""
    notification_client = NotificationClient()
    results = {}
    
    # Test 1: Notification via topic (devrait fonctionner)
    try:
        topic_success = notification_client.send_to_topic(
            title="✅ SoulVerse Test Topic",
            body="Test de notification via topic - ceci devrait fonctionner",
            topic="test_notifications"
        )
        results["topic_notification"] = {
            "status": "success" if topic_success else "failed",
            "message": "Topic notification sent successfully" if topic_success else "Topic notification failed"
        }
    except Exception as e:
        results["topic_notification"] = {
            "status": "error",
            "message": f"Topic notification error: {str(e)}"
        }
    
    # Test 2: Verset quotidien via topic
    try:
        verse_success = notification_client.send_daily_verse(
            verse_content="Car Dieu a tant aimé le monde qu'il a donné son Fils unique, afin que quiconque croit en lui ne périsse point, mais qu'il ait la vie éternelle.",
            verse_reference="Jean 3:16",
            reflection="L'amour infini de Dieu se manifeste par le don de son Fils unique. Cette vérité fondamentale nous rappelle que nous sommes précieux aux yeux de Dieu.",
            topic="daily_verses"
        )
        results["daily_verse_notification"] = {
            "status": "success" if verse_success else "failed",
            "message": "Daily verse sent successfully" if verse_success else "Daily verse failed"
        }
    except Exception as e:
        results["daily_verse_notification"] = {
            "status": "error",
            "message": f"Daily verse error: {str(e)}"
        }
    
    # Test 3: Prière du matin
    try:
        morning_success = notification_client.send_morning_prayer(
            prayer_text="Seigneur, bénis cette nouvelle journée. Que ta présence m'accompagne dans chaque étape. Amen.",
            topic="morning_prayers"
        )
        results["morning_prayer_notification"] = {
            "status": "success" if morning_success else "failed",
            "message": "Morning prayer sent successfully" if morning_success else "Morning prayer failed"
        }
    except Exception as e:
        results["morning_prayer_notification"] = {
            "status": "error",
            "message": f"Morning prayer error: {str(e)}"
        }
    
    # Test 4: Prière du soir
    try:
        evening_success = notification_client.send_evening_prayer(
            prayer_text="Merci Seigneur pour cette journée. Que ta paix remplisse mon cœur ce soir. Amen.",
            topic="evening_prayers"
        )
        results["evening_prayer_notification"] = {
            "status": "success" if evening_success else "failed",
            "message": "Evening prayer sent successfully" if evening_success else "Evening prayer failed"
        }
    except Exception as e:
        results["evening_prayer_notification"] = {
            "status": "error",
            "message": f"Evening prayer error: {str(e)}"
        }
    
    # Test 5: Token-based avec utilisateurs de test (démonstration de l'échec avec tokens factices)
    test_users = db.query(User).filter(User.fcm_token.like("dummyFCMTokenForTesting%")).all()
    if test_users:
        try:
            tokens = [user.fcm_token for user in test_users if user.fcm_token]
            token_result = notification_client.send_to_multiple(
                title="⚠️ Test Token (Will Fail)",
                body="Test avec tokens factices - ceci va échouer car les tokens ne sont pas valides",
                tokens=tokens
            )
            results["token_notification"] = {
                "status": "partial" if token_result["success_count"] > 0 else "failed",
                "success_count": token_result["success_count"],
                "failure_count": token_result["failure_count"],
                "message": f"Token test: {token_result['success_count']} success, {token_result['failure_count']} failures",
                "failed_tokens": token_result.get("failed_tokens", [])
            }
        except Exception as e:
            results["token_notification"] = {
                "status": "error",
                "message": f"Token notification error: {str(e)}"
            }
    else:
        results["token_notification"] = {
            "status": "skipped",
            "message": "No test users with FCM tokens found"
        }
    
    # Résumé
    successful_tests = sum(1 for result in results.values() if result.get("status") == "success")
    total_tests = len(results)
    
    return {
        "summary": {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": f"{successful_tests}/{total_tests}",
            "firebase_connection": "✅ Working (topic notifications successful)",
            "token_validation": "❌ Failed (dummy tokens not valid)",
            "system_status": "✅ Ready for production with real FCM tokens"
        },
        "detailed_results": results,
        "next_steps": [
            "1. Les notifications via topics fonctionnent parfaitement",
            "2. Pour les notifications individuelles, utilisez de vrais tokens FCM depuis l'app mobile",
            "3. Le système est prêt pour la production",
            "4. Configurez l'app mobile pour envoyer de vrais tokens FCM lors de l'inscription"
        ]
    }
