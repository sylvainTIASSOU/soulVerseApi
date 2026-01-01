# -*- coding: utf-8 -*-

import asyncio
import logging
import base64
from io import BytesIO
from typing import Optional, Dict, Any
import hashlib
from datetime import datetime
from pathlib import Path

# Imports conditionnels avec fallback
try:
    from PIL import Image, ImageDraw, ImageFont
    import textwrap
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning(
        "PIL not available - local image generation will be disabled")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logging.warning(
        "httpx not available - API image generation will be disabled")

from src.soul_verse_api.core.config import settings

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageGenerationService:
    """Service de génération d'images pour les versets bibliques"""

    def __init__(self):
        self.local_images_dir = Path("storage/verse_images")
        self.local_images_dir.mkdir(parents=True, exist_ok=True)

        # Configuration OpenAI DALL-E
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)

        # Configuration Stable Diffusion API (exemple: Stability AI)
        self.stability_api_key = getattr(settings, 'STABILITY_API_KEY', None)

        # Configuration Gemini (pour génération d'images)
        self.gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)

        # Template couleurs et styles
        self.color_themes = {
            "paix": {
                "background": (135, 206, 235, 255),  # Sky Blue
                "text": (25, 25, 112, 255),          # Midnight Blue
                "accent": (255, 255, 255, 255)       # White
            },
            "joie": {
                "background": (255, 215, 0, 255),    # Gold
                "text": (139, 69, 19, 255),          # Saddle Brown
                "accent": (255, 255, 255, 255)       # White
            },
            "tristesse": {
                "background": (105, 105, 105, 255),  # Dim Gray
                "text": (255, 255, 255, 255),        # White
                "accent": (173, 216, 230, 255)       # Light Blue
            },
            "anxiété": {
                "background": (147, 112, 219, 255),  # Medium Purple
                "text": (255, 255, 255, 255),        # White
                "accent": (255, 182, 193, 255)       # Light Pink
            },
            "gratitude": {
                "background": (255, 165, 0, 255),    # Orange
                "text": (139, 0, 0, 255),            # Dark Red
                "accent": (255, 255, 255, 255)       # White
            },
            "default": {
                "background": (70, 130, 180, 255),   # Steel Blue
                "text": (255, 255, 255, 255),        # White
                "accent": (255, 215, 0, 255)         # Gold
            }
        }

    def _generate_image_hash(self, text: str, reference: str, mood: str) -> str:
        """Génère un hash unique pour éviter la régénération d'images identiques"""
        content = f"{text}_{reference}_{mood}".encode('utf-8')
        return hashlib.md5(content).hexdigest()

    def _extract_visual_elements(self, verse_text: str, reference: str, ai_visual_elements: str = None) -> str:
        """
        Extrait les éléments visuels du verset pour créer un prompt détaillé

        Args:
            verse_text: Texte du verset biblique
            reference: Référence (ex: "Jean 3:16")
            ai_visual_elements: Éléments visuels suggérés par l'IA

        Returns:
            Description détaillée pour la génération d'image
        """
        # Mots-clés visuels bibliques
        visual_keywords = {
            # Nature
            "lumière": "divine light rays, golden glow, heavenly illumination",
            "eau": "flowing water, river of life, peaceful stream",
            "montagne": "majestic mountain, high peak, rocky summit",
            "vallée": "green valley, peaceful landscape",
            "mer": "calm sea, ocean waves, water expanse",
            "ciel": "heavenly sky, clouds, celestial realm",
            "soleil": "bright sun, sunrise, golden rays",
            "étoile": "shining stars, night sky, celestial lights",
            "arbre": "tree of life, olive tree, flourishing tree",
            "vigne": "vineyard, grape vines, fruit bearing",
            "fleur": "blooming flowers, lilies, roses",
            "jardin": "garden of Eden, peaceful garden",
            "désert": "desert landscape, wilderness, sandy dunes",
            "rocher": "solid rock, stone foundation, cliff",
            "source": "spring water, fountain, wellspring",

            # Symboles spirituels
            "croix": "wooden cross, crucifix, salvation symbol",
            "colombe": "white dove, Holy Spirit, peace bird",
            "agneau": "lamb of God, innocent lamb",
            "lion": "lion of Judah, majestic lion",
            "pain": "bread of life, broken bread",
            "vin": "wine chalice, communion cup",
            "couronne": "crown of thorns, crown of glory",
            "épée": "sword of the Spirit, flaming sword",
            "bouclier": "shield of faith, divine protection",
            "porte": "open door, gateway, entrance",
            "chemin": "narrow path, journey road, way forward",
            "berger": "good shepherd, shepherd with sheep",
            "brebis": "sheep flock, lost sheep",
            "temple": "holy temple, sanctuary, sacred place",
            "autel": "altar, place of sacrifice",

            # Émotions/États
            "paix": "peaceful atmosphere, calm serenity, tranquil scene",
            "joie": "joyful celebration, radiant happiness",
            "espoir": "hopeful sunrise, new beginning",
            "amour": "loving embrace, heart of compassion",
            "foi": "faithful prayer, trust in God",
            "grâce": "graceful blessing, divine favor",
            "miséricorde": "merciful compassion, forgiving love",
            "salut": "salvation light, redemption",
            "résurrection": "empty tomb, rising glory",
            "gloire": "glorious radiance, heavenly splendor"
        }

        # Extraire les éléments du texte du verset
        verse_lower = verse_text.lower()
        detected_elements = []

        for keyword, visual_desc in visual_keywords.items():
            if keyword in verse_lower:
                detected_elements.append(visual_desc)

        # Utiliser les suggestions de l'IA si disponibles
        if ai_visual_elements:
            detected_elements.insert(0, ai_visual_elements)

        # Si aucun élément détecté, utiliser des éléments génériques spirituels
        if not detected_elements:
            detected_elements = [
                "peaceful spiritual atmosphere",
                "divine light from heaven",
                "open Bible with glowing text",
                "serene landscape"
            ]

        # Limiter à 6 éléments pour ne pas surcharger
        return ", ".join(detected_elements[:6])

    async def generate_verse_image(
        self,
        verse_text: str,
        reference: str,
        mood: str = "paix",
        method: str = "local",
        ai_visual_elements: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Génère une image pour un verset biblique

        Args:
            verse_text: Texte du verset
            reference: Référence biblique (ex: "Jean 3:16")
            mood: Mood pour adapter le style
            method: Méthode de génération ("local", "dalle", "stability")
            ai_visual_elements: Éléments visuels suggérés par l'IA

        Returns:
            Dict avec path, url, method utilisée
        """
        try:
            # Vérifier si l'image existe déjà
            image_hash = self._generate_image_hash(verse_text, reference, mood)
            existing_image = await self._check_existing_image(image_hash)

            if existing_image:
                logger.info(f"Image existante trouvée: {image_hash}")
                return existing_image

            # Générer nouvelle image selon la méthode
            if method == "gemini" and self.gemini_api_key:
                result = await self._generate_with_gemini(verse_text, reference, mood, image_hash)
            elif method == "dalle" and self.openai_api_key:
                result = await self._generate_with_dalle(verse_text, reference, mood, image_hash)
            elif method == "stability" and self.stability_api_key:
                result = await self._generate_with_stability(verse_text, reference, mood, image_hash, ai_visual_elements)
            else:
                result = await self._generate_local_image(verse_text, reference, mood, image_hash)

            if result:
                logger.info(f"Image générée avec succès: {result['method']}")
                return result
            else:
                logger.error("Échec génération image")
                return None

        except Exception as e:
            logger.error(f"Erreur génération image: {e}")
            return None

    async def _check_existing_image(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """Vérifie si une image existe déjà"""
        local_path = self.local_images_dir / f"{image_hash}.png"

        if local_path.exists():
            return {
                "image_path": str(local_path),
                "image_url": f"/static/verse_images/{image_hash}.png",
                "image_hash": image_hash,
                "method": "cached",
                "generated_at": datetime.fromtimestamp(local_path.stat().st_mtime).isoformat()
            }

        return None

    async def _generate_local_image(
        self,
        verse_text: str,
        reference: str,
        mood: str,
        image_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Génère une image localement avec PIL ou fallback simple"""

        if not PIL_AVAILABLE:
            # Créer un fallback simple sans PIL
            logger.info(
                "PIL non disponible - création d'un placeholder simple")
            return await self._create_simple_placeholder(verse_text, reference, mood, image_hash)

        try:
            # Dimensions de l'image
            width, height = 800, 600

            # Thème couleur selon mood
            theme = self.color_themes.get(mood, self.color_themes["default"])

            # Créer l'image
            image = Image.new('RGBA', (width, height), theme["background"])
            draw = ImageDraw.Draw(image)

            # Charger ou créer une font
            try:
                # Essayer de charger une belle police
                font_large = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                font_medium = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                font_small = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except (OSError, IOError):
                # Fallback vers police par défaut
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()

            # Wrapper le texte pour qu'il tienne dans l'image
            wrapper = textwrap.TextWrapper(width=50)
            wrapped_verse = wrapper.wrap(verse_text)

            # Position de départ
            y_offset = 80
            line_height = 35

            # Dessiner le titre "Verset du Jour"
            title = "Verset du Jour"
            title_bbox = draw.textbbox((0, 0), title, font=font_large)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(
                ((width - title_width) // 2, 30),
                title,
                fill=theme["accent"],
                font=font_large
            )

            # Dessiner le texte du verset
            for line in wrapped_verse:
                line_bbox = draw.textbbox((0, 0), line, font=font_medium)
                line_width = line_bbox[2] - line_bbox[0]
                draw.text(
                    ((width - line_width) // 2, y_offset),
                    line,
                    fill=theme["text"],
                    font=font_medium
                )
                y_offset += line_height

            # Dessiner la référence
            ref_bbox = draw.textbbox((0, 0), reference, font=font_small)
            ref_width = ref_bbox[2] - ref_bbox[0]
            draw.text(
                ((width - ref_width) // 2, height - 60),
                reference,
                fill=theme["accent"],
                font=font_small
            )

            # Ajouter un mood indicator (petit cercle coloré)
            mood_color = {
                "paix": (0, 255, 0, 255),      # Vert
                "joie": (255, 255, 0, 255),    # Jaune
                "tristesse": (128, 128, 128, 255),  # Gris
                "anxiété": (128, 0, 128, 255),  # Violet
                "gratitude": (255, 140, 0, 255)  # Orange foncé
            }.get(mood, (255, 255, 255, 255))

            draw.ellipse(
                [width - 50, height - 50, width - 20, height - 20],
                fill=mood_color
            )

            # Sauvegarder l'image
            image_path = self.local_images_dir / f"{image_hash}.png"
            image.save(image_path, "PNG", quality=95)

            return {
                "image_path": str(image_path),
                "image_url": f"/static/verse_images/{image_hash}.png",
                "image_hash": image_hash,
                "method": "local_generation",
                "generated_at": datetime.now().isoformat(),
                "mood_theme": mood
            }

        except Exception as e:
            logger.error(f"Erreur génération locale: {e}")
            return None

    async def _create_simple_placeholder(
        self,
        verse_text: str,
        reference: str,
        mood: str,
        image_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Créer un placeholder simple sans PIL en écrivant un fichier SVG"""
        try:
            # Thèmes couleur par mood
            color_themes = {
                "paix": {"bg": "#87CEEB", "text": "#191970", "accent": "#FFFFFF"},
                "joie": {"bg": "#FFD700", "text": "#8B4513", "accent": "#FFFFFF"},
                "tristesse": {"bg": "#696969", "text": "#FFFFFF", "accent": "#ADD8E6"},
                "anxiété": {"bg": "#9370DB", "text": "#FFFFFF", "accent": "#FFB6C1"},
                "gratitude": {"bg": "#FFA500", "text": "#8B0000", "accent": "#FFFFFF"},
                "default": {"bg": "#F5F5DC", "text": "#2F4F4F", "accent": "#FFFFFF"}
            }

            theme = color_themes.get(mood, color_themes["default"])

            # Créer un SVG simple
            svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{theme['bg']}" />
      <stop offset="100%" stop-color="{theme['accent']}" />
    </linearGradient>
  </defs>
  <rect width="800" height="600" fill="url(#bgGrad)" />
  <circle cx="400" cy="150" r="80" fill="{theme['accent']}" opacity="0.3" />
  <text x="400" y="200" text-anchor="middle" fill="{theme['text']}" 
        font-family="Arial, sans-serif" font-size="24" font-weight="bold">
    📖 Verset Spirituel
  </text>
  <text x="400" y="250" text-anchor="middle" fill="{theme['text']}" 
        font-family="Arial, sans-serif" font-size="18">
    {reference}
  </text>
  <text x="400" y="320" text-anchor="middle" fill="{theme['text']}" 
        font-family="Arial, sans-serif" font-size="16" font-style="italic">
    Mood: {mood.title()}
  </text>
  <text x="400" y="400" text-anchor="middle" fill="{theme['text']}" 
        font-family="Arial, sans-serif" font-size="14" opacity="0.7">
    {verse_text[:60]}...
  </text>
  <circle cx="100" cy="500" r="8" fill="{theme['accent']}" opacity="0.6" />
  <circle cx="700" cy="500" r="8" fill="{theme['accent']}" opacity="0.6" />
  <text x="400" y="550" text-anchor="middle" fill="{theme['text']}" 
        font-family="Arial, sans-serif" font-size="12" opacity="0.5">
    SoulVerse - Méditation Biblique
  </text>
</svg>"""

            # Sauvegarder le SVG
            image_path = self.local_images_dir / \
                f"{image_hash}_placeholder.svg"
            with open(image_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            return {
                "image_path": str(image_path),
                "image_url": f"/static/verse_images/{image_hash}_placeholder.svg",
                "image_hash": image_hash,
                "method": "svg_placeholder",
                "generated_at": datetime.now().isoformat(),
                "mood_theme": mood
            }

        except Exception as e:
            logger.error(f"Erreur création placeholder: {e}")
            return None

    async def _generate_with_dalle(
        self,
        verse_text: str,
        reference: str,
        mood: str,
        image_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Génère une image avec DALL-E (OpenAI)"""
        try:
            if not HTTPX_AVAILABLE:
                logger.warning("httpx non disponible pour DALL-E")
                return None

            if not self.openai_api_key:
                logger.warning("Clé OpenAI manquante pour DALL-E")
                return None

            # Construire le prompt pour DALL-E
            mood_descriptions = {
                "paix": "peaceful, serene, calm blue and white tones",
                "joie": "joyful, bright, golden and warm colors",
                "tristesse": "gentle, comforting, soft gray and blue tones",
                "anxiété": "soothing, reassuring, purple and soft colors",
                "gratitude": "warm, thankful, orange and earth tones"
            }

            mood_desc = mood_descriptions.get(
                mood, "peaceful, spiritual, soft colors")

            prompt = f"""
            Create a beautiful, spiritual image for a Bible verse with {mood_desc}.
            Style: minimalist, elegant, typography-focused, peaceful atmosphere.
            The image should evoke {mood} and be suitable for daily meditation.
            Include subtle spiritual symbols like dove, cross, or nature elements.
            No specific text needed in the image.
            """

            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                }

                data = {
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "size": "1024x1024",
                    "quality": "standard",
                    "n": 1
                }

                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers=headers,
                    json=data
                )

                if response.status_code == 200:
                    result = response.json()
                    image_url = result["data"][0]["url"]

                    # Télécharger et sauvegarder l'image
                    image_response = await client.get(image_url)
                    if image_response.status_code == 200:
                        image_path = self.local_images_dir / \
                            f"{image_hash}_dalle.png"

                        with open(image_path, "wb") as f:
                            f.write(image_response.content)

                        return {
                            "image_path": str(image_path),
                            "image_url": f"/static/verse_images/{image_hash}_dalle.png",
                            "image_hash": image_hash,
                            "method": "dalle_3",
                            "generated_at": datetime.now().isoformat(),
                            "original_url": image_url
                        }

                logger.error(
                    f"Erreur DALL-E: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Erreur DALL-E: {e}")
            return None

    async def _generate_with_gemini(
        self,
        verse_text: str,
        reference: str,
        mood: str,
        image_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Génère une image avec Gemini (Google AI) - TEMPORAIREMENT DÉSACTIVÉ"""
        try:
            # Note: L'API Gemini pour génération d'images n'est pas encore disponible publiquement
            # Désactivé temporairement pour éviter les erreurs 401
            logger.info(
                "Génération d'images Gemini temporairement désactivée (API non disponible)")
            return None

            # Construire le prompt pour Gemini
            mood_descriptions = {
                "paix": "peaceful, serene, calm atmosphere with soft blue and white colors",
                "joie": "joyful, bright, radiant with golden and warm colors",
                "tristesse": "gentle, comforting, soft gray and blue tones",
                "anxiété": "soothing, reassuring, purple and calming colors",
                "gratitude": "warm, thankful, orange and earth tones"
            }

            mood_desc = mood_descriptions.get(
                mood, "peaceful, spiritual, soft colors")

            prompt = f"""
            Generate a beautiful spiritual image for the Bible verse: {reference}
            Text context: "{verse_text[:100]}..."
            Style: {mood_desc}, artistic, inspirational, religious art style
            Include subtle spiritual symbols like dove, cross, or nature elements.
            High quality, beautiful composition, peaceful atmosphere.
            """

            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.gemini_api_key}",
                    "Content-Type": "application/json"
                }

                # Utiliser l'API Gemini pour la génération d'images
                data = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.4,
                        "candidateCount": 1,
                        "maxOutputTokens": 2048,
                    }
                }

                # Note: URL d'exemple - l'API Gemini pour images peut différer
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={self.gemini_api_key}",
                    headers=headers,
                    json=data
                )

                if response.status_code == 200:
                    result = response.json()

                    # Traiter la réponse Gemini (adapter selon l'API réelle)
                    if "candidates" in result and result["candidates"]:
                        candidate = result["candidates"][0]

                        # Si Gemini retourne une URL d'image ou des données d'image
                        if "content" in candidate:
                            # Sauvegarder l'image générée
                            image_path = self.local_images_dir / \
                                f"{image_hash}_gemini.png"

                            # Créer une image placeholder pour l'instant
                            # En attente de l'implémentation complète de l'API Gemini images
                            if PIL_AVAILABLE:
                                from PIL import Image, ImageDraw, ImageFont
                                img = Image.new(
                                    'RGB', (512, 512), color=(220, 220, 255))
                                draw = ImageDraw.Draw(img)

                                try:
                                    font = ImageFont.truetype(
                                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                                except:
                                    font = ImageFont.load_default()

                                draw.text((50, 200), "Gemini Generated",
                                          fill=(100, 50, 150), font=font)
                                draw.text((50, 250), f"Mood: {mood}", fill=(
                                    150, 100, 200), font=font)
                                img.save(image_path)

                                return {
                                    "image_path": str(image_path),
                                    "image_url": f"/static/verse_images/{image_hash}_gemini.png",
                                    "image_hash": image_hash,
                                    "method": "gemini",
                                    "generated_at": datetime.now().isoformat(),
                                    "mood_theme": mood
                                }

                logger.error(
                    f"Erreur Gemini: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Erreur Gemini: {e}")
            return None

    async def _generate_with_stability(
        self,
        verse_text: str,
        reference: str,
        mood: str,
        image_hash: str,
        ai_visual_elements: str = None
    ) -> Optional[Dict[str, Any]]:
        """Génère une image avec Stability AI basée sur le contenu du verset"""
        try:
            if not HTTPX_AVAILABLE:
                logger.warning("httpx non disponible pour Stability AI")
                return None

            if not self.stability_api_key:
                logger.warning("Clé Stability AI manquante")
                return None

            # Extraire les éléments visuels du verset
            visual_elements = self._extract_visual_elements(
                verse_text, reference, ai_visual_elements)

            # Styles détaillés par mood
            mood_styles = {
                "paix": {
                    "atmosphere": "peaceful, serene, tranquil, calm",
                    "lighting": "soft heavenly light, gentle glow, peaceful illumination",
                    "colors": "soft blues, gentle whites, calming pastels",
                    "elements": "calm waters, peaceful dove, serene clouds"
                },
                "joie": {
                    "atmosphere": "joyful, radiant, celebratory, uplifting",
                    "lighting": "bright golden light, radiant sunshine, warm glow",
                    "colors": "golden yellows, warm oranges, vibrant colors",
                    "elements": "blooming flowers, sunrise, celebration"
                },
                "tristesse": {
                    "atmosphere": "gentle, comforting, compassionate, tender",
                    "lighting": "soft gentle light, comforting glow, tender illumination",
                    "colors": "soft grays, gentle blues, comforting tones",
                    "elements": "gentle rain, comforting embrace, peaceful refuge"
                },
                "anxiété": {
                    "atmosphere": "protective, safe, reassuring, secure",
                    "lighting": "guiding light, protective glow, beacon of hope",
                    "colors": "calming purples, soothing blues, gentle colors",
                    "elements": "strong fortress, safe harbor, guiding star"
                },
                "gratitude": {
                    "atmosphere": "thankful, abundant, blessed, appreciative",
                    "lighting": "warm candlelight, harvest glow, thanksgiving light",
                    "colors": "warm oranges, golden browns, earth tones",
                    "elements": "abundant harvest, overflowing blessings, thanksgiving"
                },
                "nouvel_an": {
                    "atmosphere": "new beginning, fresh start, hopeful, renewing",
                    "lighting": "dawn light, new morning, fresh sunrise",
                    "colors": "bright whites, fresh blues, new day colors",
                    "elements": "sunrise, new path, open door, fresh page"
                },
                "fin_annee": {
                    "atmosphere": "reflective, grateful, blessed, faithful",
                    "lighting": "warm sunset, evening glow, faithful light",
                    "colors": "golden sunset, warm earth tones, grateful colors",
                    "elements": "harvest gathered, journey completed, blessings counted"
                },
                "noel": {
                    "atmosphere": "holy, miraculous, divine, incarnate",
                    "lighting": "star light, heavenly glow, divine radiance",
                    "colors": "holy whites, celestial blues, star gold",
                    "elements": "star of Bethlehem, manger, heavenly angels"
                },
                "paques": {
                    "atmosphere": "victorious, resurrected, triumphant, glorious",
                    "lighting": "resurrection light, triumphant dawn, glory rays",
                    "colors": "brilliant whites, victory gold, glorious light",
                    "elements": "empty tomb, risen glory, victory cross"
                }
            }

            style = mood_styles.get(mood, mood_styles["paix"])

            # Construire un prompt détaillé et riche
            prompt = f"""
            Masterpiece biblical spiritual artwork depicting: {visual_elements}
            
            Verse context: {reference} - {verse_text[:100]}...
            
            Atmosphere: {style['atmosphere']}
            Lighting: {style['lighting']}
            Color palette: {style['colors']}
            Key elements: {style['elements']}
            
            Art style: highly detailed religious art, renaissance inspired, divine atmosphere,
            professional digital painting, cinematic composition, sacred art, spiritual depth,
            biblical accuracy, reverent tone, inspirational, worship-worthy
            
            Quality: 8k, ultra detailed, masterpiece, professional artwork, gallery quality,
            dramatic lighting, perfect composition, emotional depth, spiritual significance
            
            Mood: {mood}, meditative, prayer-worthy, soul touching
            """

            # Prompt négatif pour éviter les éléments indésirables
            negative_prompt = """
            low quality, blurry, distorted, ugly, bad anatomy, disfigured, poorly drawn,
            amateur, sketchy, draft, unfinished, inappropriate, dark occult, scary,
            horror, violent, gore, disturbing, evil, demonic, satanic, blasphemous,
            text overlay, watermark, signature, logo, modern elements, technology,
            photographic, realistic photo, selfie, contemporary clothing
            """

            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.stability_api_key}",
                    "Accept": "application/json"
                }

                data = {
                    "text_prompts": [
                        {
                            "text": prompt.strip(),
                            "weight": 1.0
                        },
                        {
                            "text": negative_prompt.strip(),
                            "weight": -1.0
                        }
                    ],
                    "cfg_scale": 9,  # Augmenté pour meilleure adhérence au prompt
                    "height": 1024,
                    "width": 1024,
                    "samples": 1,
                    "steps": 40,  # Augmenté pour meilleure qualité
                    "style_preset": "digital-art",  # Style artistique
                    "sampler": "K_DPMPP_2M"  # Meilleur sampler pour détails
                }

                response = await client.post(
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers=headers,
                    json=data
                )

                if response.status_code == 200:
                    result = response.json()

                    # Décoder l'image base64
                    image_data = base64.b64decode(
                        result["artifacts"][0]["base64"])

                    image_path = self.local_images_dir / \
                        f"{image_hash}_stability.png"

                    with open(image_path, "wb") as f:
                        f.write(image_data)

                    return {
                        "image_path": str(image_path),
                        "image_url": f"/static/verse_images/{image_hash}_stability.png",
                        "image_hash": image_hash,
                        "method": "stability_ai",
                        "generated_at": datetime.now().isoformat()
                    }

                logger.error(
                    f"Erreur Stability: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Erreur Stability AI: {e}")
            return None

    async def generate_multiple_methods(
        self,
        verse_text: str,
        reference: str,
        mood: str = "paix",
        ai_visual_elements: str = None
    ) -> Dict[str, Any]:
        """
        Essaie plusieurs méthodes de génération avec fallback

        Args:
            verse_text: Texte du verset
            reference: Référence biblique
            mood: Mood/occasion
            ai_visual_elements: Éléments visuels suggérés par l'IA

        Returns:
            Dict avec la meilleure image générée
        """
        methods = []

        # Ordre de préférence selon la disponibilité des clés API
        # Stability AI en priorité pour la meilleure qualité avec le contexte du verset
        if self.stability_api_key:
            methods.append("stability")
        if self.openai_api_key:
            methods.append("dalle")
        methods.append("local")  # Toujours disponible

        for method in methods:
            try:
                logger.info(
                    f"Tentative génération image avec méthode: {method}")
                result = await self.generate_verse_image(verse_text, reference, mood, method, ai_visual_elements)

                if result:
                    return result

            except Exception as e:
                logger.warning(f"Méthode {method} échouée: {e}")
                continue

        # Si tout échoue, retourner une image par défaut
        return {
            "image_path": None,
            "image_url": "/static/default_verse.png",
            "image_hash": "default",
            "method": "fallback",
            "generated_at": datetime.now().isoformat(),
            "error": "Toutes les méthodes de génération ont échoué"
        }

    async def cleanup_old_images(self, days_old: int = 7):
        """Nettoie les images anciennes"""
        try:
            import time
            current_time = time.time()

            for image_file in self.local_images_dir.glob("*.png"):
                file_age = current_time - image_file.stat().st_mtime
                if file_age > (days_old * 24 * 3600):  # Convertir jours en secondes
                    image_file.unlink()
                    logger.info(f"Image supprimée: {image_file.name}")

        except Exception as e:
            logger.error(f"Erreur nettoyage images: {e}")


# Instance globale du service
image_generation_service = ImageGenerationService()


def get_image_service() -> ImageGenerationService:
    """Dependency pour obtenir le service de génération d'images"""
    return image_generation_service
