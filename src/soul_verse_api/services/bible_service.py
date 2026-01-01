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

        # Mapping des noms de livres français → anglais (pour FreBBB)
        # La Bible FreBBB utilise des noms anglais même si c'est une traduction française
        self.book_name_mapping = {
            # Ancien Testament
            "genèse": "Genesis",
            "genesis": "Genesis",
            "exode": "Exodus",
            "exodus": "Exodus",
            "lévitique": "Leviticus",
            "levitique": "Leviticus",
            "leviticus": "Leviticus",
            "nombres": "Numbers",
            "numbers": "Numbers",
            "deutéronome": "Deuteronomy",
            "deuteronome": "Deuteronomy",
            "deuteronomy": "Deuteronomy",
            "josué": "Joshua",
            "josue": "Joshua",
            "joshua": "Joshua",
            "juges": "Judges",
            "judges": "Judges",
            "ruth": "Ruth",
            "1 samuel": "I Samuel",
            "i samuel": "I Samuel",
            "2 samuel": "II Samuel",
            "ii samuel": "II Samuel",
            "1 rois": "I Kings",
            "i kings": "I Kings",
            "2 rois": "II Kings",
            "ii kings": "II Kings",
            "1 chroniques": "I Chronicles",
            "i chronicles": "I Chronicles",
            "2 chroniques": "II Chronicles",
            "ii chronicles": "II Chronicles",
            "esdras": "Ezra",
            "ezra": "Ezra",
            "néhémie": "Nehemiah",
            "nehemie": "Nehemiah",
            "nehemiah": "Nehemiah",
            "esther": "Esther",
            "job": "Job",
            "psaume": "Psalms",
            "psaumes": "Psalms",
            "psalms": "Psalms",
            "proverbes": "Proverbs",
            "proverbs": "Proverbs",
            "ecclésiaste": "Ecclesiastes",
            "ecclesiaste": "Ecclesiastes",
            "ecclesiastes": "Ecclesiastes",
            "cantique": "Song of Solomon",
            "cantique des cantiques": "Song of Solomon",
            "song of solomon": "Song of Solomon",
            "ésaïe": "Isaiah",
            "esaïe": "Isaiah",
            "isaïe": "Isaiah",
            "esaie": "Isaiah",
            "isaie": "Isaiah",
            "isaiah": "Isaiah",
            "jérémie": "Jeremiah",
            "jeremie": "Jeremiah",
            "jeremiah": "Jeremiah",
            "lamentations": "Lamentations",
            "ézéchiel": "Ezekiel",
            "ezéchiel": "Ezekiel",
            "ezechiel": "Ezekiel",
            "ezekiel": "Ezekiel",
            "daniel": "Daniel",
            "osée": "Hosea",
            "osee": "Hosea",
            "hosea": "Hosea",
            "joël": "Joel",
            "joel": "Joel",
            "amos": "Amos",
            "abdias": "Obadiah",
            "obadiah": "Obadiah",
            "jonas": "Jonah",
            "jonah": "Jonah",
            "michée": "Micah",
            "michee": "Micah",
            "micah": "Micah",
            "nahum": "Nahum",
            "habakuk": "Habakkuk",
            "habakkuk": "Habakkuk",
            "sophonie": "Zephaniah",
            "zephaniah": "Zephaniah",
            "aggée": "Haggai",
            "aggee": "Haggai",
            "haggai": "Haggai",
            "zacharie": "Zechariah",
            "zechariah": "Zechariah",
            "malachie": "Malachi",
            "malachi": "Malachi",

            # Nouveau Testament
            "matthieu": "Matthew",
            "matthew": "Matthew",
            "marc": "Mark",
            "mark": "Mark",
            "luc": "Luke",
            "luke": "Luke",
            "jean": "John",
            "john": "John",
            "actes": "Acts",
            "actes des apôtres": "Acts",
            "acts": "Acts",
            "romains": "Romans",
            "romans": "Romans",
            "1 corinthiens": "I Corinthians",
            "i corinthiens": "I Corinthians",
            "i corinthians": "I Corinthians",
            "2 corinthiens": "II Corinthians",
            "ii corinthiens": "II Corinthians",
            "ii corinthians": "II Corinthians",
            "galates": "Galatians",
            "galatians": "Galatians",
            "éphésiens": "Ephesians",
            "ephésiens": "Ephesians",
            "ephesiens": "Ephesians",
            "ephesians": "Ephesians",
            "philippiens": "Philippians",
            "philippians": "Philippians",
            "colossiens": "Colossians",
            "colossians": "Colossians",
            "1 thessaloniciens": "I Thessalonians",
            "i thessaloniciens": "I Thessalonians",
            "i thessalonians": "I Thessalonians",
            "2 thessaloniciens": "II Thessalonians",
            "ii thessaloniciens": "II Thessalonians",
            "ii thessalonians": "II Thessalonians",
            "1 timothée": "I Timothy",
            "i timothée": "I Timothy",
            "i timothee": "I Timothy",
            "i timothy": "I Timothy",
            "2 timothée": "II Timothy",
            "ii timothée": "II Timothy",
            "ii timothee": "II Timothy",
            "ii timothy": "II Timothy",
            "tite": "Titus",
            "titus": "Titus",
            "philémon": "Philemon",
            "philemon": "Philemon",
            "hébreux": "Hebrews",
            "hebreux": "Hebrews",
            "hebrews": "Hebrews",
            "jacques": "James",
            "james": "James",
            "1 pierre": "I Peter",
            "i pierre": "I Peter",
            "i peter": "I Peter",
            "2 pierre": "II Peter",
            "ii pierre": "II Peter",
            "ii peter": "II Peter",
            "1 jean": "I John",
            "i jean": "I John",
            "i john": "I John",
            "2 jean": "II John",
            "ii jean": "II John",
            "ii john": "II John",
            "3 jean": "III John",
            "iii jean": "III John",
            "iii john": "III John",
            "jude": "Jude",
            "apocalypse": "Revelation",
            "revelation": "Revelation"
        }

    def normalize_book_name(self, book: str) -> str:
        """
        Normalise le nom d'un livre biblique pour correspondre au format de la base

        Args:
            book: Nom du livre (ex: "Jérémie", "Jean", "1 Corinthiens")

        Returns:
            Nom normalisé du livre
        """
        book_lower = book.lower().strip()
        return self.book_name_mapping.get(book_lower, book)

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
        import logging
        logger = logging.getLogger(__name__)

        bible_data = await self.load_bible_json(translation)

        # Normaliser le nom du livre
        normalized_book = self.normalize_book_name(book)
        logger.info(
            f"📖 Recherche: '{book}' → '{normalized_book}' {chapter}:{verse}")

        # Structure JSON: books -> chapters -> verses
        for bible_book in bible_data.get("books", []):
            # Comparaison case-insensitive
            if bible_book["name"].lower() == normalized_book.lower():
                logger.info(f"✅ Livre trouvé: {bible_book['name']}")
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
                logger.warning(
                    f"⚠️ Chapitre/verset non trouvé: {chapter}:{verse}")
                return None

        # Si pas trouvé, logger tous les livres disponibles pour debug
        available_books = [b["name"] for b in bible_data.get("books", [])]
        logger.warning(
            f"❌ Livre '{normalized_book}' non trouvé. Livres disponibles: {available_books[:10]}...")
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
