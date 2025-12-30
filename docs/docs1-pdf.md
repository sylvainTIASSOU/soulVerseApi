# Architecture Technique de **SoulVerse**  
*Basée sur `scrollmapper/bible_databases` + IA personnalisée + FastAPI*

---

## 📁 1. Structure du Projet

```bash
soulverse-api/
├── app/
│   ├── core/                 # Config, sécurité, logging
│   ├── models/               # Modèles SQLAlchemy
│   ├── schemas/              # Schémas Pydantic
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── users.py
│   │           ├── verses.py
│   │           ├── journal.py
│   │           └── ai.py
│   ├── services/
│   │   ├── bible_loader.py   # Chargement JSON → BDD
│   │   ├── gemini_service.py # Prompting IA
│   │   └── scheduler.py      # Envoi quotidien
│   ├── data/                 # JSON Bible (fra, ewe, en)
│   └── main.py
├── .env
├── requirements.txt
└── docker-compose.yml
```

---

## 🗃️ 2. Modèles SQLAlchemy (PostgreSQL)

### ✅ `User`
```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)  # +228 format
    role = Column(String)  # parent, entrepreneur, etc.
    preferred_translation = Column(String, default="fraLSG")
    language = Column(String, default="fr")
    created_at = Column(DateTime, default=datetime.utcnow)
```

### ✅ `BibleVerse`
*(Table polymorphe ou une par traduction – ici une seule table avec `translation`)*
```python
class BibleVerse(Base):
    __tablename__ = "bible_verses"
    id = Column(Integer, primary_key=True)
    translation = Column(String, index=True)  # ex: "fraLSG", "eeb1983"
    book = Column(String, index=True)         # ex: "Genèse"
    chapter = Column(Integer, index=True)
    verse = Column(Integer, index=True)
    text = Column(Text)
    __table_args__ = (UniqueConstraint('translation', 'book', 'chapter', 'verse'),)
```

### ✅ `CrossReference`
```python
class CrossReference(Base):
    __tablename__ = "cross_references"
    id = Column(Integer, primary_key=True)
    from_book = Column(String)
    from_chapter = Column(Integer)
    from_verse = Column(Integer)
    to_book = Column(String)
    to_chapter = Column(Integer)
    to_verse_start = Column(Integer)
    to_verse_end = Column(Integer)
    votes = Column(Integer, default=0)
```

### ✅ `DailyVerseLog`
```python
class DailyVerseLog(Base):
    __tablename__ = "daily_verse_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    verse_id = Column(Integer, ForeignKey("bible_verses.id"))
    date = Column(Date, default=date.today)
    mood = Column(String, nullable=True)  # "anxiété", "joie", etc.
    ai_reflection = Column(Text, nullable=True)
```

### ✅ `JournalEntry`
```python
class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date)
    content = Column(Text, nullable=True)
    audio_url = Column(String, nullable=True)  # chemin MinIO
    is_synced = Column(Boolean, default=False)
```

---

## 🔁 3. Workflow de Chargement des Données (JSON → BDD)

### Étape 1 : Télécharger les JSON depuis `scrollmapper`
```bash
# Dans app/data/
wget https://github.com/scrollmapper/bible_databases/raw/2025/Formats/json/fraLSG.json
wget https://github.com/scrollmapper/bible_databases/raw/2025/Formats/json/eeb1983.json
wget https://github.com/scrollmapper/bible_databases/raw/2025/Formats/json/engWEB.json
```

### Étape 2 : Script de chargement (`app/services/bible_loader.py`)
```python
def load_bible_json_to_db(translation: str, json_path: str):
    with open(json_path) as f:
        data = json.load(f)
    for book_name, chapters in data.items():
        for chap_num, verses in chapters.items():
            for verse_num, text in verses.items():
                verse = BibleVerse(
                    translation=translation,
                    book=book_name,
                    chapter=int(chap_num),
                    verse=int(verse_num),
                    text=text.strip()
                )
                db.add(verse)
    db.commit()
```

> **Exécuté une fois** au démarrage ou via script CLI.

---

## 🤖 4. Workflow d’IA (Gemini) – Verset Personnalisé

### Prompt pour Gemini (`app/services/gemini_service.py`)
```python
def build_prompt(mood: str, role: str, translation: str = "fraLSG"):
    return f"""
    Tu es un assistant spirituel chrétien bienveillant.
    Propose un seul verset biblique pertinent en {translation} pour une personne qui :
    - Se sent : {mood}
    - Est : {role}
    
    Réponds EXACTEMENT dans ce format JSON :
    {{
      "reference": "Livre Chapitre:Verset",
      "reflection": "Une courte réflexion de 1–2 phrases en français clair, empathique, sans jargon."
    }}
    """
```

### Appel à l’API
```python
async def get_personalized_verse(mood: str, role: str):
    prompt = build_prompt(mood, role)
    response = await gemini_client.generate_content(prompt)
    try:
        return json.loads(response.text)
    except:
        # Fallback : sélection aléatoire dans la BDD par thème
        return fallback_verse(mood)
```

> **Fallback** : Si IA échoue → requête SQL sur mots-clés (`WHERE text ILIKE '%paix%'`).

---

## 📅 5. Envoi Quotidien du Verset

### Mécanisme : Tâche planifiée (`app/services/scheduler.py`)
- Utilise **APScheduler** ou **Celery + Redis**
- S’exécute chaque jour à **6h00** (heure locale de Lomé)

### Logique :
1. Pour chaque utilisateur actif :
   - Récupère `mood` (si fourni la veille) ou `None`
   - Appelle `get_personalized_verse(mood, user.role)`
   - Trouve `verse_id` via `reference` → requête BDD
   - Enregistre dans `DailyVerseLog`
   - **Envoie notification push** via FCM (Firebase)

### Endpoint utilisateur :
```http
POST /api/v1/mood
{ "mood": "anxiété" }
```
→ Stocké pour le verset du **lendemain matin**.

---

## 📱 6. Endpoints API Principaux (FastAPI)

| Endpoint | Méthode | Description |
|--------|--------|------------|
| `POST /users` | `POST` | Créer compte + profil (rôle, traduction) |
| `POST /mood` | `POST` | Déclarer son émotion du jour |
| `GET /verse/today` | `GET` | Récupérer le verset du jour (avec réflexion IA) |
| `POST /journal` | `POST` | Sauvegarder texte/audio |
| `GET /journal` | `GET` | Lister les entrées |
| `GET /verse/{book}/{chapter}/{verse}` | `GET` | Lire un verset précis |
| `GET /cross-references` | `GET` | Voir liens pour un verset donné |

---

## 🌐 7. Support Multilingue

- **Interface** : déterminée par `Accept-Language` ou profil utilisateur
- **Bible** : toujours selon `user.preferred_translation`
- **IA** : toujours en **français clair** (même si traduction = éwé)
- **Fallback hors ligne** : les 7 prochains versets pré-téléchargés au lancement

---

## 🔐 8. Sécurité & Confidentialité

- **Données sensibles** (journal, émotions) : **chiffrées** si stockées cloud
- **RGPD/Togo** : pas de tracking publicitaire, pas de vente de données
- **Auth** : JWT + OAuth2 (Google/Apple)

---

## 📦 9. Déploiement (Docker Compose)

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://...
      - GEMINI_API_KEY=...
    depends_on: [db, redis]

  db:
    image: postgres:16
    volumes: [./data:/var/lib/postgresql/data]

  redis:
    image: redis:7

  traefik:
    image: traefik:v3.1
    # TLS Let's Encrypt, etc.
```

---

## 💡 10. Fonctionnalités Anticipées (Roadmap)

| Fonction | Implémentation |
|--------|---------------|
| **Mode hors ligne complet** | Pré-téléchargement hebdomadaire (Flutter + GetStorage) |
| **Partage image** | Génération côté serveur (Pillow) ou client (Flutter) |
| **Paiements Flooz/T-Money** | Webhook sécurisé + statut abonnement |
| **Églises partenaires** | Table `churches`, endpoint B2B |
| **Statistiques spirituelles** | Agrégation mensuelle via cron |
| **Audio TTS** | Intégration côté client (pas serveur) |

---

## ✅ Avantages de cette architecture

- **100 % offline-ready** grâce aux JSON locaux
- **Évolutif** : ajout de langues = nouveau JSON + `load_bible_json_to_db()`
- **IA encadrée** : fallback BDD si erreur Gemini
- **Respectueux** : pas de dépendance à des API tierces critiques
- **Localisé** : compatible Togo (flooz, langue, contexte)

---

> 📌 **Prochaine étape** :  
> Veux-tu que je te génère :
> - Le fichier `gemini_service.py` complet ?
> - Le script de migration PostgreSQL ?
> - Un exemple de requête GraphQL pour remplacer REST ?
> - La version Flutter du client ?

Dis-moi !
