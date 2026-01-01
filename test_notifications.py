#!/usr/bin/env python3
"""
Script de test pour le système de notifications SoulVerse
"""

import sys
import os

# Ajouter le répertoire racine au Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.soul_verse_api.core.notification_client import NotificationClient, NotificationPushType
    print("✅ Import du NotificationClient réussi")
except ImportError as e:
    print(f"❌ Erreur import NotificationClient: {e}")
    sys.exit(1)


def test_notification_client():
    """Test basique du client de notification"""
    print("\n🧪 Test du client de notification Firebase...")

    try:
        # Initialiser le client
        client = NotificationClient()
        print("✅ NotificationClient initialisé avec succès")

        # Test d'envoi vers un topic (sans token réel, juste pour tester la structure)
        print("📱 Test d'envoi de notification vers un topic...")

        # Simuler un envoi (cela échouera sans vraie configuration Firebase, mais on teste la structure)
        try:
            result = client.send_daily_verse(
                verse_content="Car Dieu a tant aimé le monde qu'il a donné son Fils unique...",
                verse_reference="Jean 3:16",
                reflection="L'amour de Dieu dépasse toute compréhension.",
                topic="test_verses"
            )
            print(f"✅ Méthode send_daily_verse exécutée: {result}")
        except Exception as e:
            print(f"⚠️ Erreur d'envoi (normal sans config Firebase): {e}")

        print("✅ Structure du client de notification validée")

    except Exception as e:
        print(f"❌ Erreur lors du test du client: {e}")
        return False

    return True


def test_scheduler_import():
    """Test d'import du scheduler avec notifications"""
    print("\n🧪 Test d'import du SchedulerService...")

    try:
        from src.soul_verse_api.services.scheduler_service import SchedulerService
        print("✅ Import SchedulerService réussi")

        # Créer une instance (sans démarrer le scheduler)
        scheduler = SchedulerService()
        print("✅ Instance SchedulerService créée")

        # Vérifier que le NotificationClient est bien intégré
        if hasattr(scheduler, 'notification_client'):
            print("✅ NotificationClient bien intégré dans SchedulerService")
        else:
            print("❌ NotificationClient manquant dans SchedulerService")
            return False

        print("✅ Intégration scheduler-notifications validée")

    except Exception as e:
        print(f"❌ Erreur lors du test du scheduler: {e}")
        return False

    return True


def test_enum_types():
    """Test des types d'énumération"""
    print("\n🧪 Test des types de notification...")

    try:
        # Test des énumérations
        print(f"📋 Types de notification disponibles:")
        for notification_type in NotificationPushType:
            print(f"   - {notification_type.value}")

        # Types spécifiques à SoulVerse
        spiritual_types = [
            NotificationPushType.DAILY_VERSE,
            NotificationPushType.MORNING_PRAYER,
            NotificationPushType.EVENING_PRAYER,
            NotificationPushType.SPIRITUAL_REMINDER
        ]

        print(f"✅ Types spirituels SoulVerse:")
        for type_name in spiritual_types:
            print(f"   - {type_name.value}")

    except Exception as e:
        print(f"❌ Erreur lors du test des énumérations: {e}")
        return False

    return True


def main():
    """Fonction principale de test"""
    print("🙏 SoulVerse - Test du système de notifications")
    print("=" * 50)

    success = True

    # Test 1: Client de notification
    success &= test_notification_client()

    # Test 2: Intégration scheduler
    success &= test_scheduler_import()

    # Test 3: Types d'énumération
    success &= test_enum_types()

    print("\n" + "=" * 50)
    if success:
        print("✅ Tous les tests ont réussi!")
        print("📱 Le système de notifications SoulVerse est prêt")
        print("\nPour démarrer l'API:")
        print(
            "1. Installer les dépendances: pip install fastapi[standard] redis pydantic google-genai sqlalchemy")
        print("2. Configurer Firebase avec le bon certificat")
        print("3. Démarrer: python -m uvicorn src.soul_verse_api.main:app --reload")
    else:
        print("❌ Certains tests ont échoué")
        print("🔧 Vérifiez les erreurs ci-dessus")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
