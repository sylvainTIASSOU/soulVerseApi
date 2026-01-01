# -*- coding: utf-8 -*-

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
import calendar

# Imports des services
from src.soul_verse_api.models.Models import User
from src.soul_verse_api.database.session import SessionLocal
from src.soul_verse_api.services.redis_service import RedisService
from src.soul_verse_api.services.gemini_service import GeminiService
from src.soul_verse_api.services.bible_service import BibleService
from src.soul_verse_api.core.notification_client import NotificationClient, NotificationPushType

# Import conditionnel pour le service d'images
try:
    from src.soul_verse_api.services.image_generation_service import get_image_service
    IMAGE_SERVICE_AVAILABLE = True
except ImportError:
    IMAGE_SERVICE_AVAILABLE = False
    logging.warning("Image generation service not available")

    def get_image_service():
        return None
from src.soul_verse_api.core.config import settings

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerService:
    """Service de planification pour les versets quotidiens et notifications"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.redis_service = RedisService()
        self.gemini_service = GeminiService()
        self.bible_service = BibleService()
        self.image_service = get_image_service()
        self.notification_client = NotificationClient()
        self.is_running = False  # État du planificateur

    def get_special_occasion(self, date: datetime = None) -> Optional[dict]:
        """
        Détecte si une date correspond à une occasion spéciale chrétienne

        Args:
            date: Date à vérifier (par défaut: aujourd'hui)

        Returns:
            Dictionnaire avec l'occasion et sa priorité, ou None
        """
        if date is None:
            date = datetime.now()

        day = date.day
        month = date.month
        year = date.year
        weekday = date.weekday()  # 0=Lundi, 6=Dimanche

        # Occasions fixes (haute priorité)
        fixed_occasions = {
            (1, 1): {
                "name": "nouvel_an",
                "description": "Nouvel An - Nouveaux départs et nouvelles bénédictions",
                "priority": 10,
                "themes": ["nouveau_depart", "espoir", "projets", "benediction"]
            },
            (12, 31): {
                "name": "fin_annee",
                "description": "Fin d'année - Bilan et gratitude",
                "priority": 10,
                "themes": ["gratitude", "bilan", "reconnaissance", "fidelite_divine"]
            },
            (12, 25): {
                "name": "noel",
                "description": "Noël - Naissance de Jésus-Christ",
                "priority": 10,
                "themes": ["incarnation", "salut", "amour_divin", "esperance"]
            },
            (12, 24): {
                "name": "veille_noel",
                "description": "Veille de Noël - Préparation du cœur",
                "priority": 9,
                "themes": ["attente", "preparation", "esperance"]
            },
            (1, 6): {
                "name": "epiphanie",
                "description": "Épiphanie - Manifestation du Christ aux nations",
                "priority": 8,
                "themes": ["revelation", "lumiere", "mission"]
            },
            (8, 15): {
                "name": "assomption",
                "description": "Assomption - Élévation de Marie",
                "priority": 7,
                "themes": ["espoir_celeste", "foi", "devotion"]
            },
            (11, 1): {
                "name": "toussaint",
                "description": "Toussaint - Communion des saints",
                "priority": 7,
                "themes": ["sanctification", "esperance", "communion"]
            },
        }

        # Vérifier les occasions fixes
        if (month, day) in fixed_occasions:
            logger.info(
                f"🎉 Occasion spéciale détectée: {fixed_occasions[(month, day)]['description']}")
            return fixed_occasions[(month, day)]

        # Dimanche (Jour du Seigneur) - priorité moyenne
        if weekday == 6:  # Dimanche
            return {
                "name": "dimanche",
                "description": "Jour du Seigneur - Repos et adoration",
                "priority": 5,
                "themes": ["adoration", "repos", "communion", "louange"]
            }

        # Premier jour du mois - priorité basse
        if day == 1:
            return {
                "name": "debut_mois",
                "description": f"Début du mois de {calendar.month_name[month]} - Nouvelles bénédictions",
                "priority": 4,
                "themes": ["nouveau_depart", "benediction", "provision"]
            }

        # Semaine Sainte (Pâques - calcul variable)
        easter_date = self._calculate_easter(year)
        if easter_date:
            # Dimanche de Pâques
            if date.date() == easter_date:
                return {
                    "name": "paques",
                    "description": "Pâques - Résurrection du Christ",
                    "priority": 10,
                    "themes": ["resurrection", "victoire", "vie_nouvelle", "esperance"]
                }

            # Vendredi Saint (2 jours avant Pâques)
            good_friday = easter_date - timedelta(days=2)
            if date.date() == good_friday:
                return {
                    "name": "vendredi_saint",
                    "description": "Vendredi Saint - Crucifixion du Christ",
                    "priority": 10,
                    "themes": ["sacrifice", "redemption", "amour", "salut"]
                }

            # Jeudi Saint (3 jours avant Pâques)
            maundy_thursday = easter_date - timedelta(days=3)
            if date.date() == maundy_thursday:
                return {
                    "name": "jeudi_saint",
                    "description": "Jeudi Saint - Dernière Cène",
                    "priority": 9,
                    "themes": ["communion", "service", "amour_fraternel"]
                }

            # Dimanche des Rameaux (7 jours avant Pâques)
            palm_sunday = easter_date - timedelta(days=7)
            if date.date() == palm_sunday:
                return {
                    "name": "rameaux",
                    "description": "Dimanche des Rameaux - Entrée triomphale à Jérusalem",
                    "priority": 8,
                    "themes": ["messie", "louange", "humilite"]
                }

            # Pentecôte (50 jours après Pâques)
            pentecost = easter_date + timedelta(days=49)
            if date.date() == pentecost:
                return {
                    "name": "pentecote",
                    "description": "Pentecôte - Descente du Saint-Esprit",
                    "priority": 10,
                    "themes": ["saint_esprit", "puissance", "mission", "transformation"]
                }

            # Ascension (39 jours après Pâques)
            ascension = easter_date + timedelta(days=39)
            if date.date() == ascension:
                return {
                    "name": "ascension",
                    "description": "Ascension - Élévation du Christ",
                    "priority": 9,
                    "themes": ["gloire", "esperance_celeste", "presence_divine"]
                }

        return None

    def _calculate_easter(self, year: int) -> Optional[datetime]:
        """
        Calcule la date de Pâques pour une année donnée (algorithme de Meeus)

        Args:
            year: Année

        Returns:
            Date de Pâques
        """
        try:
            a = year % 19
            b = year // 100
            c = year % 100
            d = b // 4
            e = b % 4
            f = (b + 8) // 25
            g = (b - f + 1) // 3
            h = (19 * a + b - d - g + 15) % 30
            i = c // 4
            k = c % 4
            l = (32 + 2 * e + 2 * i - h - k) % 7
            m = (a + 11 * h + 22 * l) // 451
            month = (h + l - 7 * m + 114) // 31
            day = ((h + l - 7 * m + 114) % 31) + 1

            return datetime(year, month, day).date()
        except Exception as e:
            logger.error(f"Erreur calcul date de Pâques: {e}")
            return None

    def _setup_daily_jobs(self):
        """Configure les tâches planifiées"""

        # Verset quotidien à 6h00 (heure locale Togo)
        self.scheduler.add_job(
            func=self._generate_daily_verses_job,
            trigger=CronTrigger(hour=6, minute=0, timezone="Africa/Lome"),
            id="daily_verses_generation",
            name="Génération versets quotidiens",
            replace_existing=True,
            max_instances=1
        )

        # Prière du matin à 7h00
        self.scheduler.add_job(
            func=self._send_morning_prayer_job,
            trigger=CronTrigger(hour=7, minute=0, timezone="Africa/Lome"),
            id="morning_prayer_notification",
            name="Notification prière du matin",
            replace_existing=True,
            max_instances=1
        )

        # Prière du soir à 19h00
        self.scheduler.add_job(
            func=self._send_evening_prayer_job,
            trigger=CronTrigger(hour=19, minute=0, timezone="Africa/Lome"),
            id="evening_prayer_notification",
            name="Notification prière du soir",
            replace_existing=True,
            max_instances=1
        )

        # Nettoyage cache expiré à 2h00
        self.scheduler.add_job(
            func=self._cleanup_expired_cache_job,
            trigger=CronTrigger(hour=2, minute=0, timezone="Africa/Lome"),
            id="cache_cleanup",
            name="Nettoyage cache expiré",
            replace_existing=True,
            max_instances=1
        )

        # Mise à jour statistiques utilisateurs à minuit
        self.scheduler.add_job(
            func=self._update_user_stats_job,
            trigger=CronTrigger(hour=0, minute=0, timezone="Africa/Lome"),
            id="user_stats_update",
            name="Mise à jour stats utilisateurs",
            replace_existing=True,
            max_instances=1
        )

        logger.info("Jobs planifiés configurés avec succès")

    @asynccontextmanager
    async def get_db_session(self):
        """Context manager pour les sessions de base de données"""
        db = SessionLocal()
        try:
            yield db
        except Exception as e:
            logger.error(f"Erreur de base de données: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    async def get_active_users(self) -> List[User]:
        """
        Récupère tous les utilisateurs actifs avec FCM token

        Returns:
            Liste des utilisateurs actifs
        """
        try:
            async with self.get_db_session() as db:
                users = db.query(User).filter(
                    and_(
                        User.is_active == True,
                        User.fcm_token.isnot(None),
                        User.fcm_token != ""
                    )
                ).all()

                logger.info(f"Récupéré {len(users)} utilisateurs actifs")
                return users

        except Exception as e:
            logger.error(
                f"Erreur lors de la récupération des utilisateurs: {e}")
            return []

    async def get_users_by_timezone(self, timezone: str = "Africa/Lome") -> List[User]:
        """
        Récupère les utilisateurs par fuseau horaire

        Args:
            timezone: Fuseau horaire cible

        Returns:
            Liste des utilisateurs dans ce fuseau horaire
        """
        try:
            async with self.get_db_session() as db:
                users = db.query(User).filter(
                    and_(
                        User.is_active == True,
                        User.fcm_token.isnot(None),
                        User.timezone == timezone
                    )
                ).all()

                logger.info(
                    f"Récupéré {len(users)} utilisateurs pour timezone {timezone}")
                return users

        except Exception as e:
            logger.error(f"Erreur lors de la récupération par timezone: {e}")
            return []

    async def _generate_daily_verses_job(self):
        """
        Job principal: génère les versets quotidiens pour tous les utilisateurs
        """
        logger.info("🌅 Début génération des versets quotidiens")

        try:
            # Récupérer tous les utilisateurs actifs
            users = await self.get_active_users()

            if not users:
                logger.warning("Aucun utilisateur actif trouvé")
                return

            # Traiter les utilisateurs par batch pour éviter la surcharge
            batch_size = 50
            total_processed = 0
            total_errors = 0

            for i in range(0, len(users), batch_size):
                batch = users[i:i + batch_size]
                logger.info(
                    f"Traitement du batch {i//batch_size + 1}: {len(batch)} utilisateurs")

                # Traiter le batch
                batch_results = await asyncio.gather(
                    *[self._generate_user_daily_verse(user) for user in batch],
                    return_exceptions=True
                )

                # Compter les succès/échecs
                for result in batch_results:
                    if isinstance(result, Exception):
                        total_errors += 1
                        logger.error(
                            f"Erreur traitement utilisateur: {result}")
                    else:
                        total_processed += 1

                # Pause entre les batches pour éviter la surcharge
                if i + batch_size < len(users):
                    await asyncio.sleep(1)

            logger.info(
                f"✅ Génération terminée: {total_processed} succès, {total_errors} erreurs sur {len(users)} utilisateurs")

        except Exception as e:
            logger.error(
                f"❌ Erreur critique dans génération versets quotidiens: {e}")

    async def _generate_user_daily_verse(self, user: User) -> bool:
        """
        Génère le verset quotidien pour un utilisateur spécifique

        Args:
            user: L'utilisateur pour lequel générer le verset

        Returns:
            True si succès, False sinon
        """
        try:
            user_id = str(user.id)

            # Vérifier si le verset du jour existe déjà
            cached_verse = await self.redis_service.get_daily_verse(user_id)
            if cached_verse:
                logger.debug(
                    f"Verset déjà en cache pour utilisateur {user_id[:8]}...")
                return True

            # Récupérer le mood de l'utilisateur (depuis DB ou Redis)
            mood = user.mood or await self.redis_service.get_user_mood(user_id) or "paix"

            # Vérifier s'il y a une occasion spéciale aujourd'hui
            special_occasion = self.get_special_occasion()

            # Prioriser l'occasion spéciale sur le mood si elle existe
            if special_occasion and special_occasion.get("priority", 0) >= 7:
                # Occasion de haute priorité : utiliser l'occasion au lieu du mood
                logger.info(
                    f"🎊 Génération avec occasion spéciale prioritaire: {special_occasion['description']}")
                context = special_occasion["name"]
                context_type = "occasion"
            else:
                # Pas d'occasion prioritaire : utiliser le mood
                context = mood
                context_type = "mood"
                if special_occasion:
                    logger.info(
                        f"📅 Occasion détectée mais mood prioritaire: {special_occasion['description']}")

            # Générer le verset avec l'IA
            try:
                ai_response = await self.gemini_service.get_personalized_verse(
                    mood=mood,
                    special_occasion=special_occasion
                )
            except Exception as e:
                logger.warning(
                    f"Erreur IA pour utilisateur {user_id[:8]}...: {e}")
                # Fallback vers un verset prédéfini
                ai_response = await self._get_fallback_verse(mood, special_occasion)

            if not ai_response:
                logger.error(
                    f"Impossible de générer verset pour utilisateur {user_id[:8]}...")
                return False

            # Récupérer le texte complet du verset depuis la Bible
            translation = user.preferred_translation or "FreBBB"
            bible_verse = await self.get_bible_verse_from_reference(
                ai_response["reference"],
                translation
            )

            # Générer l'image du verset (si le service est disponible)
            verse_image = None
            try:
                if self.image_service and IMAGE_SERVICE_AVAILABLE:
                    # Extraire les éléments visuels suggérés par l'IA
                    ai_visual_elements = ai_response.get(
                        "visual_elements", None)

                    if bible_verse:
                        verse_image = await self.image_service.generate_multiple_methods(
                            verse_text=bible_verse.text,
                            reference=ai_response["reference"],
                            mood=special_occasion.get(
                                "name") if special_occasion else mood,
                            ai_visual_elements=ai_visual_elements
                        )
                    else:
                        # Fallback avec texte de la réflexion si pas de verset
                        verse_image = await self.image_service.generate_multiple_methods(
                            verse_text=ai_response.get("reflection", "")[
                                :100] + "...",
                            reference=ai_response["reference"],
                            mood=special_occasion.get(
                                "name") if special_occasion else mood,
                            ai_visual_elements=ai_visual_elements
                        )
                else:
                    logger.info(
                        "Service de génération d'images non disponible - verset sans image")
            except Exception as e:
                logger.warning(
                    f"Erreur génération image pour {user_id[:8]}...: {e}")

            # Construire les données complètes du verset
            verse_data = {
                "verse": bible_verse.dict() if bible_verse else None,
                "ai_response": ai_response,
                "ai_reflection": ai_response.get("reflection", ""),
                "verse_image": verse_image,
                "mood_context": mood,
                "special_occasion": special_occasion.get("name") if special_occasion else None,
                "occasion_description": special_occasion.get("description") if special_occasion else None,
                "reference": ai_response["reference"],
                "generated_at": datetime.now().isoformat(),
                "user_id": user_id,
                "translation": user.preferred_translation or "FreBBB",
                "has_full_verse": bible_verse is not None,
                "has_image": verse_image is not None and verse_image.get("image_url") != "/static/default_verse.png"
            }

            # Mettre en cache
            success = await self.redis_service.cache_daily_verse(user_id, verse_data)

            if success:
                logger.debug(
                    f"✅ Verset généré et mis en cache pour {user_id[:8]}...")

                # Envoyer notification push si l'utilisateur a un token FCM
                if hasattr(user, 'fcm_token') and user.fcm_token:
                    try:
                        # Préparer les données pour la notification
                        verse_text = bible_verse.text if bible_verse else ai_response.get("reflection", "")[
                            :100] + "..."
                        image_url = verse_image.get("image_url") if verse_image and verse_image.get(
                            "image_url") != "/static/default_verse.png" else None

                        # Envoyer la notification
                        notification_sent = self.notification_client.send_daily_verse(
                            verse_content=verse_text,
                            verse_reference=ai_response["reference"],
                            reflection=ai_response.get("reflection"),
                            image_url=image_url,
                            tokens=[user.fcm_token]
                        )

                        if notification_sent:
                            logger.debug(
                                f"📱 Notification envoyée pour {user_id[:8]}...")
                        else:
                            logger.warning(
                                f"❌ Échec envoi notification pour {user_id[:8]}...")

                    except Exception as notif_error:
                        logger.error(
                            f"Erreur envoi notification pour {user_id[:8]}...: {notif_error}")
                else:
                    logger.debug(
                        f"👤 Utilisateur {user_id[:8]}... sans token FCM - notification ignorée")
            else:
                logger.warning(
                    f"⚠️ Verset généré mais erreur cache pour {user_id[:8]}...")

            return True

        except Exception as e:
            logger.error(
                f"Erreur génération verset utilisateur {user.id}: {e}")
            return False

    async def get_bible_verse_from_reference(self, reference: str, translation: str = "FreBBB"):
        """
        Récupère le texte complet d'un verset depuis une référence

        Args:
            reference: Référence du verset (ex: "Jean 3:16", "Jérémie 29:11")
            translation: Traduction biblique à utiliser

        Returns:
            BibleVerse si trouvé, None sinon
        """
        try:
            logger.info(f"🔍 Parsing référence: '{reference}'")

            # Parser la référence
            ref_parts = reference.strip().split()

            if len(ref_parts) >= 2:
                # Le dernier élément devrait être chapitre:verset
                chapter_verse_part = ref_parts[-1]
                # Tout le reste est le nom du livre
                book = " ".join(ref_parts[:-1])

                logger.info(
                    f"📖 Livre: '{book}', Partie: '{chapter_verse_part}'")

                # Parser chapitre:verset
                chapter_verse = chapter_verse_part.split(":")

                if len(chapter_verse) == 2:
                    try:
                        chapter = int(chapter_verse[0])
                        verse_num = int(chapter_verse[1])

                        logger.info(
                            f"📍 Recherche: {book} {chapter}:{verse_num}")

                        # Récupérer le verset complet depuis la Bible
                        bible_verse = await self.bible_service.get_verse(
                            translation, book, chapter, verse_num
                        )

                        if bible_verse:
                            logger.info(
                                f"✅ Verset trouvé: {bible_verse.text[:50]}...")
                        else:
                            logger.warning(
                                f"⚠️ Verset non trouvé: {book} {chapter}:{verse_num}")

                        return bible_verse

                    except ValueError as ve:
                        logger.warning(f"❌ Erreur conversion nombres: {ve}")
                else:
                    logger.warning(
                        f"❌ Format chapitre:verset invalide: '{chapter_verse_part}'")
            else:
                logger.warning(f"❌ Référence trop courte: '{reference}'")

        except Exception as e:
            logger.warning(f"❌ Erreur parsing référence '{reference}': {e}")

        return None

    async def _get_fallback_verse(self, mood: str, special_occasion: dict = None) -> dict:
        """
        Verset de fallback si l'IA échoue

        Args:
            mood: Le mood de l'utilisateur
            special_occasion: Occasion spéciale si elle existe

        Returns:
            Dictionnaire avec le verset de fallback
        """
        # Versets pour occasions spéciales (prioritaire)
        occasion_verses = {
            "nouvel_an": {
                "reference": "Lamentations 3:22-23",
                "reflection": "Les bontés de l'Éternel ne sont pas épuisées, Ses compassions ne prennent pas fin; Elles se renouvellent chaque matin. Grande est Ta fidélité! Que cette nouvelle année soit remplie de Ses bénédictions."
            },
            "fin_annee": {
                "reference": "Psaume 103:2",
                "reflection": "Mon âme, bénis l'Éternel, et n'oublie aucun de Ses bienfaits! En cette fin d'année, prenons le temps de nous souvenir de toutes Ses grâces et de Lui rendre gloire pour Sa fidélité."
            },
            "noel": {
                "reference": "Jean 1:14",
                "reflection": "La Parole a été faite chair, et elle a habité parmi nous. Aujourd'hui, célébrons l'amour infini de Dieu qui s'est manifesté dans la naissance de Jésus-Christ, notre Sauveur."
            },
            "paques": {
                "reference": "1 Corinthiens 15:20",
                "reflection": "Mais maintenant, Christ est ressuscité des morts, Il est les prémices de ceux qui sont morts. Christ est vivant! Cette victoire sur la mort nous donne l'espérance éternelle."
            },
            "vendredi_saint": {
                "reference": "Jean 3:16",
                "reflection": "Car Dieu a tant aimé le monde qu'Il a donné Son Fils unique. Aujourd'hui, nous méditons sur le sacrifice ultime de Jésus pour notre salut."
            },
            "pentecote": {
                "reference": "Actes 2:4",
                "reflection": "Et ils furent tous remplis du Saint-Esprit. Aujourd'hui, célébrons la puissance transformatrice de l'Esprit Saint dans nos vies."
            },
            "dimanche": {
                "reference": "Psaume 95:1-2",
                "reflection": "Venez, chantons avec allégresse à l'Éternel! Poussons des cris de joie vers le rocher de notre salut. Bon dimanche, jour du Seigneur!"
            }
        }

        # Si occasion spéciale, utiliser son verset
        if special_occasion and special_occasion.get("name") in occasion_verses:
            return occasion_verses[special_occasion["name"]]

        # Sinon, versets par mood
        fallback_verses = {
            "paix": {
                "reference": "Jean 14:27",
                "reflection": "Que la paix du Christ demeure en votre cœur. Même dans les moments difficiles, Il est votre refuge."
            },
            "joie": {
                "reference": "Psaume 118:24",
                "reflection": "Ce jour que l'Éternel a fait, réjouissons-nous et soyons dans l'allégresse !"
            },
            "tristesse": {
                "reference": "Psaume 34:19",
                "reflection": "L'Éternel est près de ceux qui ont le cœur brisé. Il vous console dans vos peines."
            },
            "anxiété": {
                "reference": "Philippiens 4:6-7",
                "reflection": "Ne vous inquiétez de rien, mais en toute chose, exposez vos besoins à Dieu par des prières et des supplications."
            },
            "gratitude": {
                "reference": "1 Thessaloniciens 5:18",
                "reflection": "Rendez grâces en toutes choses, car c'est à votre égard la volonté de Dieu en Jésus-Christ."
            }
        }

        return fallback_verses.get(mood, fallback_verses["paix"])

    async def _cleanup_expired_cache_job(self):
        """
        Job de nettoyage: supprime les caches expirés
        """
        logger.info("🧹 Début nettoyage du cache expiré")

        try:
            # Invalidate les versets d'hier et avant
            yesterday = (datetime.now() - timedelta(days=1)
                         ).strftime("%Y-%m-%d")
            await self.redis_service.invalidate_daily_verses(yesterday)

            # Autres nettoyages si nécessaire
            logger.info("✅ Nettoyage cache terminé")

        except Exception as e:
            logger.error(f"❌ Erreur nettoyage cache: {e}")

    async def _update_user_stats_job(self):
        """
        Job statistiques: met à jour les statistiques des utilisateurs
        """
        logger.info("📊 Début mise à jour statistiques utilisateurs")

        try:
            users = await self.get_active_users()

            # Mise à jour last_active pour les utilisateurs qui ont récupéré leur verset
            active_today = 0

            for user in users:
                user_id = str(user.id)
                daily_verse = await self.redis_service.get_daily_verse(user_id)

                if daily_verse:
                    active_today += 1

            logger.info(
                f"📈 Stats: {active_today}/{len(users)} utilisateurs actifs aujourd'hui")

        except Exception as e:
            logger.error(f"❌ Erreur mise à jour stats: {e}")

    async def _send_morning_prayer_job(self):
        """Job pour envoyer les notifications de prière du matin"""
        logger.info("🌅 Début envoi notifications prière du matin")

        try:
            # Détecter l'occasion spéciale du jour
            special_occasion = self.get_special_occasion()

            # Générer la prière du matin avec l'IA
            mood = "paix"  # Mood par défaut pour les prières globales
            try:
                prayer = await self.gemini_service.generate_morning_prayer(mood, special_occasion)
            except Exception as e:
                logger.warning(f"Erreur génération prière IA: {e}")
                prayer = await self.gemini_service._get_fallback_morning_prayer(mood, special_occasion)

            # Préparer les données de la prière
            prayer_data = {
                "prayer_title": prayer.get("prayer_title", "Prière du Matin"),
                "prayer_text": prayer.get("prayer_text", ""),
                "blessing": prayer.get("blessing", "Que Dieu te bénisse aujourd'hui. Amen."),
                "suggested_verse": prayer.get("suggested_verse", ""),
                "special_occasion": special_occasion.get("name") if special_occasion else None,
                "occasion_description": special_occasion.get("description") if special_occasion else None,
                "generated_at": datetime.now().isoformat(),
                "prayer_type": "morning"
            }

            # Mettre en cache la prière globale
            await self.redis_service.cache_morning_prayer(prayer_data)

            # Envoyer via topic pour tous les utilisateurs abonnés
            success = self.notification_client.send_morning_prayer(
                # Texte court pour notification
                prayer_text=prayer_data["prayer_text"][:100] + "...",
                topic="morning_prayers"
            )

            if success:
                logger.info("✅ Notifications prière du matin envoyées")
            else:
                logger.warning(
                    "⚠️ Échec partiel envoi notifications prière du matin")

        except Exception as e:
            logger.error(f"❌ Erreur envoi notifications prière du matin: {e}")

    async def _send_evening_prayer_job(self):
        """Job pour envoyer les notifications de prière du soir"""
        logger.info("🌙 Début envoi notifications prière du soir")

        try:
            # Détecter l'occasion spéciale du jour
            special_occasion = self.get_special_occasion()

            # Générer la prière du soir avec l'IA
            mood = "paix"  # Mood par défaut pour les prières globales
            try:
                prayer = await self.gemini_service.generate_evening_prayer(mood, special_occasion)
            except Exception as e:
                logger.warning(f"Erreur génération prière IA: {e}")
                prayer = await self.gemini_service._get_fallback_evening_prayer(mood, special_occasion)

            # Préparer les données de la prière
            prayer_data = {
                "prayer_title": prayer.get("prayer_title", "Prière du Soir"),
                "prayer_text": prayer.get("prayer_text", ""),
                "blessing": prayer.get("blessing", "Que tu reposes dans la paix de Dieu. Amen."),
                "suggested_verse": prayer.get("suggested_verse", ""),
                "special_occasion": special_occasion.get("name") if special_occasion else None,
                "occasion_description": special_occasion.get("description") if special_occasion else None,
                "generated_at": datetime.now().isoformat(),
                "prayer_type": "evening"
            }

            # Mettre en cache la prière globale
            await self.redis_service.cache_evening_prayer(prayer_data)

            # Envoyer via topic pour tous les utilisateurs abonnés
            success = self.notification_client.send_evening_prayer(
                # Texte court pour notification
                prayer_text=prayer_data["prayer_text"][:100] + "...",
                topic="evening_prayers"
            )

            if success:
                logger.info("✅ Notifications prière du soir envoyées")
            else:
                logger.warning(
                    "⚠️ Échec partiel envoi notifications prière du soir")

        except Exception as e:
            logger.error(f"❌ Erreur envoi notifications prière du soir: {e}")

    def start(self):
        """Démarre le planificateur"""
        if not self.is_running:
            try:
                self.scheduler.start()
                self.is_running = True
                logger.info("📅 Planificateur démarré avec succès")

                # Afficher les jobs configurés
                jobs = self.scheduler.get_jobs()
                logger.info(f"Jobs actifs: {len(jobs)}")
                for job in jobs:
                    logger.info(
                        f"  - {job.name} (ID: {job.id}) - Prochaine exécution: {job.next_run_time}")

            except Exception as e:
                logger.error(f"❌ Erreur démarrage planificateur: {e}")
                raise
        else:
            logger.warning("⚠️ Planificateur déjà démarré")

    def stop(self):
        """Arrête le planificateur"""
        if self.is_running:
            try:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("⛔ Planificateur arrêté")
            except Exception as e:
                logger.error(f"❌ Erreur arrêt planificateur: {e}")
        else:
            logger.warning("⚠️ Planificateur déjà arrêté")

    def get_status(self) -> dict:
        """
        Retourne le statut du planificateur

        Returns:
            Dictionnaire avec les informations de statut
        """
        try:
            jobs = self.scheduler.get_jobs() if self.is_running else []

            return {
                "running": self.is_running,
                "jobs_count": len(jobs),
                "jobs": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                        "trigger": str(job.trigger)
                    }
                    for job in jobs
                ],
                "timezone": "Africa/Lome",
                "status_checked_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Erreur récupération statut: {e}")
            return {
                "running": False,
                "error": str(e),
                "status_checked_at": datetime.now().isoformat()
            }

    async def trigger_daily_verses_manually(self) -> dict:
        """
        Déclenche manuellement la génération des versets quotidiens

        Returns:
            Résultat de l'opération
        """
        logger.info("🔄 Génération manuelle des versets quotidiens déclenchée")

        try:
            await self._generate_daily_verses_job()
            return {
                "success": True,
                "message": "Génération manuelle terminée avec succès",
                "triggered_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Erreur génération manuelle: {e}")
            return {
                "success": False,
                "error": str(e),
                "triggered_at": datetime.now().isoformat()
            }


# Instance globale du scheduler
scheduler_service = SchedulerService()


def get_scheduler() -> SchedulerService:
    """Dependency pour obtenir le service scheduler"""
    return scheduler_service
