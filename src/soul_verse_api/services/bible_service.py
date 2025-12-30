import requests
import json
from typing import Dict, Optional, List
import asyncio
from src.soul_verse_api.core.config import settings
from src.soul_verse_api.schemas.verse_schema import BibleVerse


class BibleService:
    def __init__(self):
        self.github_base_url = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json"
        self.available_translations = {
            "FreBBB": "FreBBB.json",      # Français Bible Bovet Bonnet
            "KJV": "KJV.json",            # King James Version
            "FreCrampon": "FreCrampon.json"  # Bible Crampon
        }

    async def load_bible_json(self, translation: str) -> Dict:
        """Charge une traduction Bible depuis GitHub"""
        if translation not in self.available_translations:
            raise ValueError(f"Traduction {translation} non disponible")

        url = f"{self.github_base_url}/{self.available_translations[translation]}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Erreur chargement Bible {translation}: {e}")

    async def get_verse(self, translation: str, book: str, chapter: int, verse: int) -> Optional[BibleVerse]:
        """Récupère un verset spécifique"""
        bible_data = await self.load_bible_json(translation)

        # Structure JSON: books -> chapters -> verses
        for bible_book in bible_data.get("books", []):
            if bible_book["name"].lower() == book.lower():
                for bible_chapter in bible_book["chapters"]:
                    if bible_chapter["chapter"] == chapter:
                        for bible_verse in bible_chapter["verses"]:
                            if bible_verse["verse"] == verse:
                                return BibleVerse(
                                    book=bible_book["name"],
                                    chapter=chapter,
                                    verse=verse,
                                    text=bible_verse["text"],
                                    translation=translation
                                )
        return None

    async def search_verses_by_keywords(self, translation: str, keywords: List[str]) -> List[BibleVerse]:
        """Recherche des versets par mots-clés pour fallback IA"""
        bible_data = await self.load_bible_json(translation)
        results = []

        for book in bible_data.get("books", []):
            for chapter in book["chapters"]:
                for verse in chapter["verses"]:
                    text_lower = verse["text"].lower()
                    if any(keyword.lower() in text_lower for keyword in keywords):
                        results.append(BibleVerse(
                            book=book["name"],
                            chapter=chapter["chapter"],
                            verse=verse["verse"],
                            text=verse["text"],
                            translation=translation
                        ))
                        if len(results) >= 10:  # Limite résultats
                            break
        return results
