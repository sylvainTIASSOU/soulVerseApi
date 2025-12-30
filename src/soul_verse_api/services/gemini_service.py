import google.generativeai as genai
from typing import Dict, Optional
import json
from src.soul_verse_api.core.config import settings
from src.soul_verse_api.schemas.verse_schema import BibleVerse, VerseWithReflection


class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')

    async def build_prompt(self, mood: str, role: str, translation: str = "FreBBB") -> str:
        return f"""
        Tu es un assistant spirituel chrétien bienveillant spécialisé dans l'encouragement biblique.
        
        Contexte:
        - La personne se sent: {mood}
        - Son rôle/situation: {role}
        - Traduction souhaitée: {translation}
        
        Instructions:
        1. Propose UN SEUL verset biblique pertinent en français qui correspond à cette émotion
        2. Assure-toi que le verset existe réellement dans la Bible
        3. Donne une réflexion courte (2-3 phrases) empathique et encourageante
        
        Réponds EXACTEMENT dans ce format JSON:
        {{
          "reference": "Livre Chapitre:Verset",
          "reflection": "Une réflexion encourageante en français simple, sans jargon religieux."
        }}
        
        Exemple pour anxiété:
        {{
          "reference": "Philippiens 4:6",
          "reflection": "Dieu comprend tes inquiétudes et Il veut que tu viennes vers Lui avec tout ce qui te préoccupe. Il y a une paix qui dépasse notre compréhension qui t'attend."
        }}
        """

    async def get_personalized_verse(self, mood: str, role: str = "croyant", translation: str = "FreBBB") -> Dict:
        """Génère un verset personnalisé avec l'IA Gemini"""
        try:
            prompt = await self.build_prompt(mood, role, translation)
            response = await self.model.generate_content_async(prompt)

            # Parse réponse JSON
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]

            result = json.loads(response_text)

            # Validation format
            if "reference" not in result or "reflection" not in result:
                raise ValueError("Format réponse IA invalide")

            return result

        except Exception as e:
            # Fallback: verset par défaut selon mood
            return await self.get_fallback_verse(mood)

    async def get_fallback_verse(self, mood: str) -> Dict:
        """Fallback si IA échoue - versets pré-définis par mood"""
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
