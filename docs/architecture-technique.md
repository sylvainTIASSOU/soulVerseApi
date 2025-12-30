# 📋 **SoulVerse API - Architecture Technique Adaptée**
*FastAPI + Bible JSON + Redis + IA Gemini + FCM Notifications*

---

## 🎯 **Analyse du Besoin**

Basé sur votre demande, voici les adaptations clés par rapport au document original :

### ✅ **Modifications principales :**
- ❌ **Suppression de la base de données PostgreSQL** (pas d'abonnements payants)
- ✅ **Utilisation directe des JSON Bible depuis GitHub**
- ✅ **Redis pour le cache temporaire** (expiration 2h)
- ✅ **Stockage minimal utilisateur** (FCM token, modèle téléphone, etc.)
- ✅ **Pas d'authentification complexe** (système simplifié)

---

## 📁 **1. Structure du Projet Adaptée**

```bash
soulverse-api/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration Redis, Gemini, FCM
│   │   ├── security.py            # Simple JWT pour sessions
│   │   └── exceptions.py          # Gestion erreurs personnalisées
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py               # Modèles Pydantic utilisateur
│   │   ├── verse.py              # Modèles Pydantic versets
│   │   └── journal.py            # Modèles Pydantic journal
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── requests.py           # Schémas requêtes API
│   │   └── responses.py          # Schémas réponses API
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── users.py      # Gestion utilisateurs (FCM, mood)
│   │           ├── verses.py     # Récupération versets
│   │           ├── journal.py    # Journal utilisateur
│   │           ├── ai.py         # Endpoints IA Gemini
│   │           └── notifications.py # Gestion FCM
│   ├── services/
│   │   ├── __init__.py
│   │   ├── bible_service.py      # Chargement JSON Bible depuis GitHub
│   │   ├── gemini_service.py     # Intégration IA Gemini
│   │   ├── redis_service.py      # Cache Redis
│   │   ├── notification_service.py # FCM Push notifications
│   │   └── scheduler_service.py  # Planification versets quotidiens
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── helpers.py            # Fonctions utilitaires
│   │   └── constants.py          # Constantes globales
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── cors.py              # Configuration CORS
│   └── main.py                   # Point d'entrée FastAPI
├── storage/
│   └── user_data.json           # Stockage simple utilisateurs (FCM, etc.)
├── .env                         # Variables d'environnement
├── requirements.txt             # Dépendances Python
├── docker-compose.yml           # Docker Redis + API
├── README.md                    # Documentation principale
└── docs/
    ├── api-documentation.md     # Documentation API complète
    ├── deployment.md           # Guide déploiement
    └── architecture.md         # Architecture détaillée
```

---

## 🗃️ **2. Modèles de Données Simplifiés (Pydantic)**

### ✅ **User Model** (`app/models/user.py`)
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    user_id: str                    # UUID unique
    fcm_token: str                  # Token Firebase Cloud Messaging
    phone_model: Optional[str]      # Modèle téléphone (pour debug)
    preferred_translation: str = "FreBBB"  # Traduction Bible préférée
    language: str = "fr"            # Langue interface
    timezone: str = "Africa/Lome"   # Fuseau horaire
    mood: Optional[str]             # Dernier mood déclaré
    created_at: datetime
    last_active: datetime

class UserMood(BaseModel):
    user_id: str
    mood: str                       # anxiété, joie, tristesse, etc.
    declared_at: datetime

class UserJournal(BaseModel):
    user_id: str
    entry_date: str                 # YYYY-MM-DD
    text_content: Optional[str]
    audio_url: Optional[str]        # Lien fichier audio si disponible
    created_at: datetime
```

### ✅ **Bible Verse Model** (`app/models/verse.py`)
```python
from pydantic import BaseModel
from typing import Optional, List

class BibleVerse(BaseModel):
    book: str                       # "Genesis", "Matthew", etc.
    chapter: int
    verse: int
    text: str
    translation: str                # "FreBBB", "KJV", etc.
    
class VerseWithReflection(BaseModel):
    verse: BibleVerse
    ai_reflection: str              # Réflexion générée par IA
    mood_context: Optional[str]     # Mood ayant inspiré le verset
    generated_at: datetime

class DailyVerseCache(BaseModel):
    user_id: str
    date: str                       # YYYY-MM-DD
    verse: VerseWithReflection
    cached_at: datetime
    expires_at: datetime            # 2h après création
```

---

## 🔁 **3. Services Principaux**

### 📖 **Bible Service** (`app/services/bible_service.py`)
```python
import requests
import json
from typing import Dict, Optional, List
import asyncio
from app.core.config import settings

class BibleService:
    def __init__(self):
        self.github_base_url = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json"
        self.available_translations = {
            "FreBBB": "FreBBB.json",      # Français Bible Bovet Bonnet
            "KJV": "KJV.json",            # King James Version
            "FreCrampon": "FreCrampon.json" # Bible Crampon
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
```

### 🤖 **Gemini AI Service** (`app/services/gemini_service.py`)
```python
import google.generativeai as genai
from typing import Dict, Optional
import json
from app.core.config import settings
from app.models.verse import BibleVerse, VerseWithReflection

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
```

### ⚡ **Redis Service** (`app/services/redis_service.py`)
```python
import redis
import json
from typing import Optional, Dict
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.verse import DailyVerseCache

class RedisService:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        self.cache_duration = 7200  # 2 heures en secondes
    
    async def cache_daily_verse(self, user_id: str, verse_data: Dict):
        """Cache le verset quotidien d'un utilisateur"""
        cache_key = f"daily_verse:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
        
        cache_data = {
            "user_id": user_id,
            "date": datetime.now().strftime('%Y-%m-%d'),
            "verse_data": verse_data,
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=self.cache_duration)).isoformat()
        }
        
        self.redis.setex(cache_key, self.cache_duration, json.dumps(cache_data))
    
    async def get_daily_verse(self, user_id: str, date: str = None) -> Optional[Dict]:
        """Récupère le verset quotidien en cache"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
            
        cache_key = f"daily_verse:{user_id}:{date}"
        cached = self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_user_mood(self, user_id: str, mood: str):
        """Cache le mood utilisateur pour le lendemain"""
        cache_key = f"user_mood:{user_id}"
        mood_data = {
            "mood": mood,
            "declared_at": datetime.now().isoformat()
        }
        
        # Cache jusqu'au lendemain 6h
        tomorrow_6am = datetime.now().replace(hour=6, minute=0, second=0) + timedelta(days=1)
        ttl = int((tomorrow_6am - datetime.now()).total_seconds())
        
        self.redis.setex(cache_key, ttl, json.dumps(mood_data))
    
    async def get_user_mood(self, user_id: str) -> Optional[str]:
        """Récupère le mood utilisateur en cache"""
        cache_key = f"user_mood:{user_id}"
        cached = self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)["mood"]
        return None
    
    async def cache_bible_translation(self, translation: str, data: Dict):
        """Cache une traduction Bible complète (durée plus longue)"""
        cache_key = f"bible_translation:{translation}"
        self.redis.setex(cache_key, 86400, json.dumps(data))  # 24h
    
    async def get_bible_translation(self, translation: str) -> Optional[Dict]:
        """Récupère une traduction Bible en cache"""
        cache_key = f"bible_translation:{translation}"
        cached = self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None
```

### 📱 **Notification Service FCM** (`app/services/notification_service.py`)
```python
import firebase_admin
from firebase_admin import credentials, messaging
from typing import List
import json
import time
from app.core.config import settings

class NotificationService:
    def __init__(self):
        # Initialiser Firebase Admin SDK
        if not firebase_admin._apps:
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": settings.FIREBASE_PROJECT_ID,
                "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
                "client_email": settings.FIREBASE_CLIENT_EMAIL
            })
            firebase_admin.initialize_app(cred)
    
    async def send_daily_verse_notification(self, fcm_token: str, verse_ref: str, reflection_preview: str):
        """Envoie notification push verset quotidien"""
        message = messaging.Message(
            notification=messaging.Notification(
                title="🌅 Votre verset du jour",
                body=f"{verse_ref} - {reflection_preview[:80]}..."
            ),
            data={
                "type": "daily_verse",
                "verse_reference": verse_ref,
                "timestamp": str(int(time.time()))
            },
            token=fcm_token
        )
        
        try:
            response = messaging.send(message)
            return {"success": True, "message_id": response}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_bulk_notifications(self, notifications: List[Dict]):
        """Envoie notifications en masse pour versets quotidiens"""
        messages = []
        
        for notif in notifications:
            messages.append(messaging.Message(
                notification=messaging.Notification(
                    title="🌅 Votre verset du jour",
                    body=f"{notif['verse_ref']} - {notif['reflection'][:80]}..."
                ),
                data={
                    "type": "daily_verse",
                    "verse_reference": notif['verse_ref']
                },
                token=notif['fcm_token']
            ))
        
        try:
            response = messaging.send_all(messages)
            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }
        except Exception as e:
            return {"error": str(e)}
```

---

## 📱 **4. Endpoints API FastAPI**

### 🔐 **Utilisateurs** (`app/api/v1/endpoints/users.py`)
```python
from fastapi import APIRouter, HTTPException
from app.models.user import User, UserMood
from app.services.redis_service import RedisService
import uuid
from datetime import datetime

router = APIRouter()
redis_service = RedisService()

@router.post("/register")
async def register_user(fcm_token: str, phone_model: str = None):
    """Enregistre un nouvel utilisateur avec token FCM"""
    user_id = str(uuid.uuid4())
    
    user = User(
        user_id=user_id,
        fcm_token=fcm_token,
        phone_model=phone_model,
        created_at=datetime.now(),
        last_active=datetime.now()
    )
    
    # Stockage simple dans Redis (pas de DB)
    await redis_service.cache_user_data(user_id, user.dict())
    
    return {"user_id": user_id, "status": "registered"}

@router.post("/mood")
async def declare_mood(user_id: str, mood: str):
    """Déclare le mood pour le verset du lendemain"""
    valid_moods = ["anxiété", "joie", "tristesse", "fatigue", "reconnaissance", "colère", "paix"]
    
    if mood not in valid_moods:
        raise HTTPException(status_code=400, detail="Mood non valide")
    
    await redis_service.cache_user_mood(user_id, mood)
    
    return {"message": f"Mood '{mood}' enregistré pour demain matin"}
```

### 📖 **Versets** (`app/api/v1/endpoints/verses.py`)
```python
from fastapi import APIRouter, HTTPException
from app.services.bible_service import BibleService
from app.services.gemini_service import GeminiService
from app.services.redis_service import RedisService
from typing import Optional
from datetime import datetime

router = APIRouter()
bible_service = BibleService()
gemini_service = GeminiService()
redis_service = RedisService()

@router.get("/today")
async def get_daily_verse(user_id: str):
    """Récupère le verset du jour (avec IA)"""
    # Vérifier cache Redis d'abord
    cached_verse = await redis_service.get_daily_verse(user_id)
    if cached_verse:
        return cached_verse
    
    # Récupérer mood utilisateur
    mood = await redis_service.get_user_mood(user_id) or "paix"
    
    # Générer verset avec IA
    ai_response = await gemini_service.get_personalized_verse(mood)
    
    # Parser référence (ex: "Jean 3:16")
    ref_parts = ai_response["reference"].split()
    book = " ".join(ref_parts[:-1])
    chapter_verse = ref_parts[-1].split(":")
    chapter, verse = int(chapter_verse[0]), int(chapter_verse[1])
    
    # Récupérer texte depuis Bible JSON
    bible_verse = await bible_service.get_verse("FreBBB", book, chapter, verse)
    
    if not bible_verse:
        raise HTTPException(status_code=404, detail="Verset non trouvé")
    
    result = {
        "verse": bible_verse.dict(),
        "ai_reflection": ai_response["reflection"],
        "mood_context": mood,
        "generated_at": datetime.now().isoformat()
    }
    
    # Mettre en cache Redis
    await redis_service.cache_daily_verse(user_id, result)
    
    return result

@router.get("/{book}/{chapter}/{verse}")
async def get_specific_verse(book: str, chapter: int, verse: int, translation: str = "FreBBB"):
    """Récupère un verset spécifique"""
    bible_verse = await bible_service.get_verse(translation, book, chapter, verse)
    
    if not bible_verse:
        raise HTTPException(status_code=404, detail="Verset non trouvé")
    
    return bible_verse.dict()
```

---

## ⏰ **5. Planificateur de Versets Quotidiens**

### 📅 **Scheduler Service** (`app/services/scheduler_service.py`)
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.notification_service import NotificationService
from app.services.redis_service import RedisService
from app.services.gemini_service import GeminiService
import json

class VerseScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.notification_service = NotificationService()
        self.redis_service = RedisService()
        self.gemini_service = GeminiService()
    
    def start(self):
        """Démarre le planificateur"""
        # Chaque jour à 6h00 (heure de Lomé)
        self.scheduler.add_job(
            self.send_daily_verses,
            CronTrigger(hour=6, minute=0, timezone="Africa/Lome"),
            id="daily_verses",
            max_instances=1
        )
        
        self.scheduler.start()
    
    async def send_daily_verses(self):
        """Envoie les versets quotidiens à tous les utilisateurs"""
        # Récupérer liste utilisateurs depuis Redis
        user_keys = self.redis_service.redis.keys("user_data:*")
        notifications = []
        
        for user_key in user_keys:
            user_data = json.loads(self.redis_service.redis.get(user_key))
            user_id = user_data["user_id"]
            fcm_token = user_data["fcm_token"]
            
            # Récupérer mood de la veille
            mood = await self.redis_service.get_user_mood(user_id) or "paix"
            
            # Générer verset avec IA
            ai_response = await self.gemini_service.get_personalized_verse(mood)
            
            notifications.append({
                "fcm_token": fcm_token,
                "verse_ref": ai_response["reference"],
                "reflection": ai_response["reflection"]
            })
        
        # Envoyer notifications push en masse
        result = await self.notification_service.send_bulk_notifications(notifications)
        
        print(f"Versets quotidiens envoyés: {result['success_count']} succès, {result['failure_count']} échecs")
```

---

## 🔧 **6. Configuration et Variables d'Environnement**

### ⚙️ **Config** (`app/core/config.py`)
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "SoulVerse API"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID: str
    FIREBASE_PRIVATE_KEY: str
    FIREBASE_CLIENT_EMAIL: str
    
    # Bible Configuration
    DEFAULT_TRANSLATION: str = "FreBBB"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 📄 **Variables d'environnement** (`.env`)
```env
# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# Firebase FCM
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API
DEBUG=True
```

---

## 🚀 **7. Docker Compose**

### 🐳 **Docker Compose** (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  # API FastAPI
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID}
      - FIREBASE_PRIVATE_KEY=${FIREBASE_PRIVATE_KEY}
      - FIREBASE_CLIENT_EMAIL=${FIREBASE_CLIENT_EMAIL}
    depends_on:
      - redis
    volumes:
      - ./storage:/app/storage
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

### 🔨 **Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📚 **8. Documentation API Complète**

### 📋 **Endpoints Principaux**

| Method | Endpoint | Description | Paramètres |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/users/register` | Enregistre utilisateur | `fcm_token`, `phone_model` |
| `POST` | `/api/v1/users/mood` | Déclare mood pour lendemain | `user_id`, `mood` |
| `GET` | `/api/v1/verses/today` | Verset quotidien personnalisé | `user_id` |
| `GET` | `/api/v1/verses/{book}/{chapter}/{verse}` | Verset spécifique | `book`, `chapter`, `verse`, `translation` |
| `POST` | `/api/v1/journal` | Ajouter entrée journal | `user_id`, `content`, `audio_url` |
| `GET` | `/api/v1/journal` | Récupérer journal | `user_id`, `date_from`, `date_to` |

### 🎯 **Cas d'Usage Principaux**

1. **Utilisateur ouvre l'app** → Enregistrement automatique avec FCM token
2. **Utilisateur déclare son mood** → Cache Redis pour verset du lendemain  
3. **6h00 chaque matin** → IA génère versets personnalisés + push notifications
4. **Utilisateur consulte verset** → Cache Redis (2h) pour performances
5. **Utilisateur écrit journal** → Stockage simple local + sync optionnelle

---

## 🌐 **9. Déploiement & Infrastructure**

### ☁️ **Options de déploiement :**

1. **Heroku + Redis Cloud** (Simple, gratuit)
2. **DigitalOcean Droplet** (VPS économique)  
3. **Google Cloud Run** (Serverless, auto-scale)
4. **Railway** (Alternative moderne à Heroku)

### 📦 **Installation & Lancement**

```bash
# 1. Cloner le repo
git clone https://github.com/votre-repo/soulverse-api
cd soulverse-api

# 2. Installer dépendances
pip install -r requirements.txt

# 3. Configurer variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API

# 4. Lancer avec Docker
docker-compose up -d

# 5. Vérifier API
curl http://localhost:8000/api/v1/health
```

### 📄 **Requirements.txt**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
redis==5.0.1
pydantic==2.5.2
python-dotenv==1.0.0
google-generativeai==0.3.2
firebase-admin==6.4.0
apscheduler==3.10.4
requests==2.31.0
python-multipart==0.0.6
```

---

## 💡 **10. Fonctionnalités Clés & Avantages**

### ✅ **Points Forts de cette Architecture :**

- **🔥 Sans base de données** → Pas de frais récurrents DB
- **⚡ Redis ultra-rapide** → Cache 2h, performances optimales  
- **📖 Bible JSON directe** → Données fraîches depuis GitHub
- **🤖 IA Gemini intégrée** → Versets personnalisés intelligents
- **📱 Notifications push** → FCM pour engagement quotidien
- **🐳 Docker ready** → Déploiement simplifié partout
- **🌍 Multilingue préparé** → Support traductions multiples
- **💾 Stockage minimal** → Juste FCM + mood + journal
- **🔒 Sécurité simple** → JWT léger, pas de mots de passe

### 🚀 **Roadmap Futures Fonctionnalités :**

- **Mode hors ligne** → Cache Bible en local (mobile)
- **Partage versets** → Génération d'images avec verset
- **Groupes de prière** → Fonctionnalités communautaires  
- **Statistiques** → Dashboard progress spirituel
- **API WhatsApp** → Versets par WhatsApp Business
- **Multi-langues** → Éwé, Kabiyè, Kotokoli pour Togo

---

## 🛠️ **11. Point d'Entrée Principal**

### 🚀 **Main.py** (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints import users, verses, journal, notifications
from app.services.scheduler_service import VerseScheduler
import asyncio

# Initialiser FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="SoulVerse API - Versets bibliques personnalisés avec IA"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes API
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(verses.router, prefix=f"{settings.API_V1_STR}/verses", tags=["verses"])
app.include_router(journal.router, prefix=f"{settings.API_V1_STR}/journal", tags=["journal"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])

# Planificateur versets quotidiens
scheduler = VerseScheduler()

@app.on_event("startup")
async def startup_event():
    """Démarre le planificateur au lancement de l'API"""
    scheduler.start()
    print("🚀 SoulVerse API démarrée")
    print("📅 Planificateur versets quotidiens actif")

@app.on_event("shutdown")
async def shutdown_event():
    """Arrête le planificateur proprement"""
    scheduler.scheduler.shutdown()
    print("⛔ SoulVerse API arrêtée")

@app.get("/")
async def root():
    return {"message": "🙏 SoulVerse API - Votre compagnon spirituel quotidien"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SoulVerse API"}
```

---

## 🎯 **Conclusion**

Cette architecture **FastAPI + Redis + Bible JSON + Gemini IA** répond parfaitement à vos besoins :

✅ **Pas de base de données** → Économies maximales  
✅ **Données Bible actualisées** → JSON depuis GitHub  
✅ **Cache intelligent Redis** → Performance + expiration 2h  
✅ **IA personnalisée** → Versets adaptés au mood  
✅ **Push notifications** → Engagement quotidien  
✅ **Architecture simple** → Déploiement et maintenance faciles  

**Prêt à développer ?** Cette base solide vous permet de créer une app spirituelle moderne et engageante pour les utilisateurs togolais ! 🇹🇬

---

## 📞 **Support Technique**

- **Documentation API** : `http://localhost:8000/docs` (Swagger UI)
- **Logs application** : Consultables via Docker ou cloud provider
- **Monitoring Redis** : Interface Redis Commander ou CLI
- **Tests endpoints** : Utilisez Postman ou curl

---

*Développé avec ❤️ pour la communauté spirituelle du Togo*