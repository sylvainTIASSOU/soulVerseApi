import google.genai as genai
from typing import Dict, Optional
import json
from src.soul_verse_api.core.config import settings
from src.soul_verse_api.schemas.verse_schema import BibleVerse, VerseWithReflection


class GeminiService:
    def __init__(self):
        # Configuration pour la nouvelle API google.genai
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def build_prompt(self, mood: str, role: str, translation: str = "FreBBB", special_occasion: dict = None) -> str:
        # Si une occasion spéciale est présente, l'intégrer dans le prompt
        if special_occasion:
            occasion_context = f"""
        OCCASION SPÉCIALE (PRIORITAIRE):
        - Événement: {special_occasion.get('description', '')}
        - Thèmes spirituels: {', '.join(special_occasion.get('themes', []))}
        
        ⚠️ IMPORTANT: Cette occasion spéciale doit PRIMER sur l'émotion de l'utilisateur.
        Choisis un verset qui correspond parfaitement à cette occasion spirituelle.
        """
        else:
            occasion_context = ""

        return f"""
        Tu es un PASTEUR expérimenté et bienveillant qui enseigne les Écritures à ses disciples avec sagesse et profondeur.
        
        Contexte:
        - La personne se sent: {mood}
        - Son rôle/situation: {role}
        - Traduction souhaitée: {translation}
        {occasion_context}
        
        Instructions:
        1. {'Si une OCCASION SPÉCIALE est présente, choisis un verset qui correspond PARFAITEMENT à cet événement chrétien (Noël, Pâques, Nouvel An, etc.)' if special_occasion else 'Propose UN SEUL verset biblique pertinent en français qui correspond à cette émotion'}
        2. Assure-toi que le verset existe réellement dans la Bible
        3. Comme un PASTEUR qui prêche et enseigne, donne une réflexion DÉTAILLÉE et PROFONDE (5-7 phrases minimum) qui:
           - EXPLIQUE le contexte biblique du verset
           - DÉVELOPPE la signification spirituelle profonde
           - APPLIQUE le verset à la vie quotidienne du croyant
           - ENCOURAGE avec des exemples concrets
           - INSPIRE à l'action et à la foi
           - Utilise un langage accessible mais riche en enseignement biblique
        
        Réponds EXACTEMENT dans ce format JSON:
        {{
          "reference": "Livre Chapitre:Verset",
          "reflection": "Une réflexion pastorale DÉTAILLÉE qui explique, enseigne et encourage comme un pasteur à ses disciples. MINIMUM 5-7 phrases riches en enseignement biblique.",
          "visual_elements": "Éléments visuels du verset pour illustration: ex. 'lumière divine, colombe, chemin montagneux, eau vive'"
        }}
        
        Exemple pour Nouvel An:
        {{
          "reference": "Lamentations 3:22-23",
          "reflection": "Mes bien-aimés, ce passage des Lamentations nous révèle une vérité puissante: la fidélité de Dieu se renouvelle chaque matin comme l'aurore qui chasse les ténèbres. Le prophète Jérémie, au milieu des ruines de Jérusalem, a découvert que même dans la désolation la plus profonde, les compassions de l'Éternel ne s'épuisent jamais. En cette nouvelle année qui s'ouvre devant nous, comprenons que chaque jour est une page blanche où Dieu écrit de nouvelles grâces. Comme la manne tombait fraîche chaque matin pour Israël dans le désert, ainsi Sa miséricorde nous attend au réveil. Ne portons pas les fardeaux d'hier dans ce nouveau chapitre - Dieu nous appelle à marcher dans la confiance, sachant qu'Il est fidèle pour accomplir ce qu'Il a commencé en nous. Que cette année soit marquée par notre foi en Sa fidélité inébranlable!",
          "visual_elements": "aurore lumineuse, ciel nouveau, manne céleste, page blanche, chemin éclairé par lumière divine"
        }}
        
        Exemple pour anxiété (sans occasion):
        {{
          "reference": "Philippiens 4:6-7",
          "reflection": "Frères et sœurs, l'apôtre Paul nous donne ici un remède divin contre l'anxiété. Remarquez qu'il ne dit pas 'ne vous inquiétez de rien parce que tout ira bien', mais plutôt il nous montre OÙ déposer nos fardeaux. Quand Paul a écrit ces mots, il était en prison, enchaîné, et pourtant il avait découvert le secret de la paix: tout exposer à Dieu par la prière. Le mot grec utilisé pour 'prière' implique une conversation intime, pas une récitation formelle. Dieu veut que tu Lui parles de tout - tes peurs, tes doutes, tes questions. Et la promesse est magnifique: une paix qui dépasse toute compréhension humaine viendra garder ton cœur et tes pensées. Cette paix n'est pas l'absence de problèmes, mais la présence de Dieu au milieu de tes tempêtes. Aujourd'hui, prends le temps de déposer tes soucis dans la prière, et laisse Sa paix inonder ton âme.",
          "visual_elements": "mains en prière, lumière apaisante, tempête calmée, cœur protégé, forteresse divine"
        }}
        """

    async def get_personalized_verse(self, mood: str, role: str = "croyant", translation: str = "FreBBB", special_occasion: dict = None) -> Dict:
        """Génère un verset personnalisé avec l'IA Gemini"""
        try:
            prompt = await self.build_prompt(mood, role, translation, special_occasion)

            # Nouvelle API google.genai
            response = await self.client.aio.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": prompt}]}]
            )

            # Parse réponse JSON
            response_text = response.candidates[0].content.parts[0].text.strip(
            )
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]

            result = json.loads(response_text)

            # Validation format
            if "reference" not in result or "reflection" not in result:
                raise ValueError("Format réponse IA invalide")

            return result

        except Exception as e:
            # Fallback: verset par défaut selon mood ou occasion
            return await self.get_fallback_verse(mood, special_occasion)

    async def get_fallback_verse(self, mood: str, special_occasion: dict = None) -> Dict:
        """Fallback si IA échoue - versets pré-définis par mood ou occasion"""

        # Versets pour occasions spéciales (prioritaire)
        occasion_fallbacks = {
            "nouvel_an": {
                "reference": "Lamentations 3:22-23",
                "reflection": "Les compassions de l'Éternel se renouvellent chaque matin. En cette nouvelle année, confie-toi en Sa fidélité infinie."
            },
            "fin_annee": {
                "reference": "Psaume 103:2",
                "reflection": "Mon âme, bénis l'Éternel, et n'oublie aucun de Ses bienfaits! Prenons le temps de nous souvenir de toutes Ses grâces en cette fin d'année."
            },
            "noel": {
                "reference": "Jean 1:14",
                "reflection": "La Parole a été faite chair et elle a habité parmi nous. Célébrons aujourd'hui l'amour de Dieu manifesté en Jésus-Christ."
            },
            "paques": {
                "reference": "1 Corinthiens 15:20",
                "reflection": "Christ est ressuscité des morts! Cette victoire sur la mort nous donne l'espérance éternelle."
            },
            "vendredi_saint": {
                "reference": "Jean 3:16",
                "reflection": "Car Dieu a tant aimé le monde qu'Il a donné Son Fils unique. Méditons aujourd'hui sur ce sacrifice d'amour."
            },
            "pentecote": {
                "reference": "Actes 2:4",
                "reflection": "Ils furent tous remplis du Saint-Esprit. Célébrons la puissance transformatrice de l'Esprit dans nos vies."
            },
            "dimanche": {
                "reference": "Psaume 95:1-2",
                "reflection": "Venez, chantons avec allégresse à l'Éternel! Bon dimanche, jour du Seigneur!"
            }
        }

        # Si occasion spéciale, la prioriser
        if special_occasion and special_occasion.get("name") in occasion_fallbacks:
            return occasion_fallbacks[special_occasion["name"]]

        # Sinon, fallback par mood
        fallbacks = {
            "anxiété": {
                "reference": "Philippiens 4:6-7",
                "reflection": "Tu peux déposer tes soucis devant Dieu dans la prière. Il promet de te donner une paix qui dépasse toute compréhension."
            },
            "joie": {
                "reference": "Psaume 118:24",
                "reflection": "Ce jour est un cadeau de Dieu. Réjouis-toi et sois reconnaissant(e) pour toutes Ses bénédictions dans ta vie."
            },
            "tristesse": {
                "reference": "Psaume 34:18",
                "reflection": "Dieu est proche de ceux qui ont le cœur brisé. Il comprend ta douleur et veut te consoler."
            },
            "default": {
                "reference": "Jérémie 29:11",
                "reflection": "Dieu a de beaux projets pour ta vie. Même dans l'incertitude, tu peux faire confiance à Sa bienveillance."
            }
        }

        return fallbacks.get(mood, fallbacks["default"])

    async def generate_morning_prayer(self, mood: str = "paix", special_occasion: dict = None) -> Dict:
        """
        Génère une prière du matin personnalisée avec l'IA Gemini

        Args:
            mood: État émotionnel de l'utilisateur
            special_occasion: Occasion spéciale chrétienne si applicable

        Returns:
            Dictionnaire avec la prière et les métadonnées
        """
        try:
            # Construire le prompt pour la prière du matin
            if special_occasion:
                occasion_context = f"""
                OCCASION SPÉCIALE (PRIORITAIRE):
                - Événement: {special_occasion.get('description', '')}
                - Thèmes spirituels: {', '.join(special_occasion.get('themes', []))}
                
                Cette prière du MATIN doit être adaptée à cette occasion.
                """
            else:
                occasion_context = ""

            prompt = f"""
            Tu es un PASTEUR qui guide ses fidèles dans la prière matinale.
            
            Contexte:
            - Moment: MATIN - Début de journée
            - État émotionnel: {mood}
            {occasion_context}
            
            Instructions:
            1. Compose une PRIÈRE DU MATIN authentique et profonde (4-6 phrases)
            2. {'Intègre l\'occasion spéciale dans la prière' if special_occasion else 'Adapte la prière à l\'état émotionnel'}
            3. Structure de la prière:
               - Adoration: Reconnaitre qui est Dieu
               - Gratitude: Remercier pour la nouvelle journée
               - Supplication: Demander Sa présence et Sa guidance
               - Engagement: S'engager à vivre pour Lui aujourd'hui
            4. Ton pastoral, chaleureux, inspirant
            5. Inclure une bénédiction finale
            
            Réponds EXACTEMENT dans ce format JSON:
            {{
              "prayer_title": "Titre de la prière (ex: 'Prière du Matin - Nouvel An')",
              "prayer_text": "Texte complet de la prière, riche et profond",
              "blessing": "Bénédiction finale courte",
              "suggested_verse": "Référence biblique en lien (ex: 'Psaume 5:3')"
            }}
            
            Exemple pour Nouvel An:
            {{
              "prayer_title": "Prière du Matin - Nouvelle Année",
              "prayer_text": "Père céleste, en ce premier matin d'une nouvelle année, nous venons devant Ton trône avec des cœurs reconnaissants. Tu as été fidèle hier, Tu es présent aujourd'hui, et Tu seras là demain. Nous Te remettons cette année entière - nos rêves, nos projets, nos incertitudes. Guide nos pas sur le chemin que Tu as préparé pour nous. Que chaque jour soit marqué par Ta présence, chaque décision éclairée par Ta sagesse, et chaque épreuve transformée par Ta grâce. Nous choisissons de marcher dans la foi, sachant que Tu es avec nous.",
              "blessing": "Que l'Éternel te bénisse et te garde en cette nouvelle année. Amen.",
              "suggested_verse": "Lamentations 3:22-23"
            }}
            """

            # Générer avec Gemini
            response = await self.client.aio.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": prompt}]}]
            )

            response_text = response.candidates[0].content.parts[0].text.strip(
            )
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]

            result = json.loads(response_text)

            # Validation
            if "prayer_text" not in result:
                raise ValueError("Format réponse IA invalide")

            return result

        except Exception as e:
            print(f"Erreur génération prière du matin: {e}")
            return await self._get_fallback_morning_prayer(mood, special_occasion)

    async def generate_evening_prayer(self, mood: str = "paix", special_occasion: dict = None) -> Dict:
        """
        Génère une prière du soir personnalisée avec l'IA Gemini

        Args:
            mood: État émotionnel de l'utilisateur
            special_occasion: Occasion spéciale chrétienne si applicable

        Returns:
            Dictionnaire avec la prière et les métadonnées
        """
        try:
            # Construire le prompt pour la prière du soir
            if special_occasion:
                occasion_context = f"""
                OCCASION SPÉCIALE (PRIORITAIRE):
                - Événement: {special_occasion.get('description', '')}
                - Thèmes spirituels: {', '.join(special_occasion.get('themes', []))}
                
                Cette prière du SOIR doit être adaptée à cette occasion.
                """
            else:
                occasion_context = ""

            prompt = f"""
            Tu es un PASTEUR qui guide ses fidèles dans la prière du soir.
            
            Contexte:
            - Moment: SOIR - Fin de journée
            - État émotionnel: {mood}
            {occasion_context}
            
            Instructions:
            1. Compose une PRIÈRE DU SOIR authentique et profonde (4-6 phrases)
            2. {'Intègre l\'occasion spéciale dans la prière' if special_occasion else 'Adapte la prière à l\'état émotionnel'}
            3. Structure de la prière:
               - Reconnaissance: Reconnaître la présence de Dieu durant la journée
               - Bilan: Remercier pour les bénédictions du jour
               - Repentance: Confesser les manquements
               - Repos: Demander Sa paix et Sa protection pour la nuit
            4. Ton apaisant, réconfortant, rassurant
            5. Inclure une bénédiction finale pour la nuit
            
            Réponds EXACTEMENT dans ce format JSON:
            {{
              "prayer_title": "Titre de la prière (ex: 'Prière du Soir - Paix')",
              "prayer_text": "Texte complet de la prière, riche et apaisant",
              "blessing": "Bénédiction finale pour la nuit",
              "suggested_verse": "Référence biblique en lien (ex: 'Psaume 4:8')"
            }}
            
            Exemple pour Fin d'année:
            {{
              "prayer_title": "Prière du Soir - Fin d'Année",
              "prayer_text": "Seigneur, alors que ce jour s'achève et que cette année touche à sa fin, nous venons devant Toi avec des cœurs remplis de gratitude. Tu nous as portés à travers chaque saison, chaque épreuve, chaque victoire. Nous Te remettons toutes les joies et les peines de cette année, sachant que Tu as travaillé toutes choses pour notre bien. Pardonne nos erreurs, reçois nos remerciements, et accorde-nous un repos paisible cette nuit. Que nous nous réveillions demain avec des cœurs renouvelés, prêts à embrasser tout ce que Tu as préparé.",
              "blessing": "Que tu reposes dans la paix du Seigneur cette nuit. Amen.",
              "suggested_verse": "Psaume 103:2"
            }}
            """

            # Générer avec Gemini
            response = await self.client.aio.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": prompt}]}]
            )

            response_text = response.candidates[0].content.parts[0].text.strip(
            )
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]

            result = json.loads(response_text)

            # Validation
            if "prayer_text" not in result:
                raise ValueError("Format réponse IA invalide")

            return result

        except Exception as e:
            print(f"Erreur génération prière du soir: {e}")
            return await self._get_fallback_evening_prayer(mood, special_occasion)

    async def _get_fallback_morning_prayer(self, mood: str, special_occasion: dict = None) -> Dict:
        """Prière du matin de fallback si l'IA échoue"""

        # Prières pour occasions spéciales
        occasion_prayers = {
            "nouvel_an": {
                "prayer_title": "Prière du Matin - Nouvel An",
                "prayer_text": "Père céleste, en ce premier matin d'une nouvelle année, nous Te louons pour Ta fidélité. Tu renouvelles nos forces chaque jour et Tes compassions sont nouvelles chaque matin. Nous Te confions cette année qui commence, nos rêves et nos projets. Guide-nous, protège-nous, et que Ta volonté soit faite dans nos vies. Que ce soit une année de croissance spirituelle et de bénédictions.",
                "blessing": "Que Dieu bénisse cette nouvelle année et te guide dans tous tes chemins. Amen.",
                "suggested_verse": "Lamentations 3:22-23"
            },
            "dimanche": {
                "prayer_title": "Prière du Matin - Dimanche",
                "prayer_text": "Seigneur Jésus, en ce jour du Seigneur, nous venons T'adorer et Te célébrer. Merci pour ce temps de repos et de communion avec Toi. Prépare nos cœurs pour recevoir Ta Parole aujourd'hui. Que notre culte soit agréable à Tes yeux et que nous repartions fortifiés et encouragés pour la semaine à venir.",
                "blessing": "Que ce dimanche soit béni et rempli de Ta présence. Amen.",
                "suggested_verse": "Psaume 95:1-2"
            }
        }

        if special_occasion and special_occasion.get("name") in occasion_prayers:
            return occasion_prayers[special_occasion["name"]]

        # Prières par mood
        mood_prayers = {
            "paix": {
                "prayer_title": "Prière du Matin - Paix",
                "prayer_text": "Seigneur, en ce nouveau jour, je viens chercher Ta paix. Que Ton Esprit Saint calme mon cœur et mes pensées. Aide-moi à marcher dans Ta présence tout au long de cette journée, sachant que Tu es avec moi à chaque instant.",
                "blessing": "Que la paix de Dieu garde ton cœur aujourd'hui. Amen.",
                "suggested_verse": "Jean 14:27"
            },
            "joie": {
                "prayer_title": "Prière du Matin - Joie",
                "prayer_text": "Père céleste, merci pour ce jour que Tu as créé! Je me réjouis en Toi et en Tes bontés. Que ma joie en Toi soit ma force aujourd'hui, et que je puisse partager cette joie avec ceux que je rencontre.",
                "blessing": "Que ta journée soit remplie de la joie du Seigneur. Amen.",
                "suggested_verse": "Néhémie 8:10"
            }
        }

        return mood_prayers.get(mood, mood_prayers["paix"])

    async def _get_fallback_evening_prayer(self, mood: str, special_occasion: dict = None) -> Dict:
        """Prière du soir de fallback si l'IA échoue"""

        # Prières pour occasions spéciales
        occasion_prayers = {
            "fin_annee": {
                "prayer_title": "Prière du Soir - Fin d'Année",
                "prayer_text": "Seigneur, alors que cette année touche à sa fin, nous Te remercions pour Ta fidélité constante. Tu nous as portés à travers chaque jour, chaque défi. Nous Te louons pour toutes Tes bénédictions. Pardonne-nous nos manquements et aide-nous à entrer dans la nouvelle année avec des cœurs renouvelés.",
                "blessing": "Que tu reposes dans la paix de Dieu cette nuit. Amen.",
                "suggested_verse": "Psaume 103:2"
            },
            "dimanche": {
                "prayer_title": "Prière du Soir - Dimanche",
                "prayer_text": "Père céleste, merci pour ce jour de repos et d'adoration. Merci pour Ta Parole qui a nourri nos âmes. Alors que nous entrons dans une nouvelle semaine, nous Te demandons Ta présence et Ta guidance. Que nous vivions pour Ta gloire dans tout ce que nous faisons.",
                "blessing": "Que tu aies une nuit paisible dans les bras du Seigneur. Amen.",
                "suggested_verse": "Psaume 4:8"
            }
        }

        if special_occasion and special_occasion.get("name") in occasion_prayers:
            return occasion_prayers[special_occasion["name"]]

        # Prières par mood
        mood_prayers = {
            "paix": {
                "prayer_title": "Prière du Soir - Paix",
                "prayer_text": "Seigneur, merci pour cette journée. Je Te remets toutes mes préoccupations et mes soucis. Accorde-moi un sommeil paisible, sachant que Tu veilles sur moi. Que je me réveille demain rafraîchi et prêt à Te servir.",
                "blessing": "Que tu dormes dans la paix de Christ. Amen.",
                "suggested_verse": "Psaume 4:8"
            },
            "gratitude": {
                "prayer_title": "Prière du Soir - Gratitude",
                "prayer_text": "Père céleste, mon cœur déborde de reconnaissance pour toutes Tes bontés aujourd'hui. Merci pour Ta présence fidèle, pour Ta provision, et pour Ton amour sans fin. Je m'endors ce soir avec un cœur reconnaissant.",
                "blessing": "Que la gratitude remplisse ton cœur cette nuit. Amen.",
                "suggested_verse": "1 Thessaloniciens 5:18"
            }
        }

        return mood_prayers.get(mood, mood_prayers["paix"])
