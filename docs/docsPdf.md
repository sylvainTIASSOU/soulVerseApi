# Architecture Technique Complète de **SoulVerse**  
*Basée sur `scrollmapper/bible_databases` (JSON) + document technique fourni + API FastAPI*  
**Version : MVP Offline-First, Sans Compte, Respectueuse des Licences**

---

## 📁 1. Structure du Projet

```
soulverse-api/
├── app/
│   ├── core/                 # Config, sécurité, logging
│   ├── models/               # Modèles SQLAlchemy
│   ├── schemas/              # Schémas Pydantic
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── content.py   # versets, prières, plans
│   │           └── metadata.py  # traductions, licences
│   ├── services/
│   │   ├── bible_loader.py      # Chargement JSON → BDD
│   │   ├── ai_selector.py       # IA responsable (RAG)
│   │   └── scheduler.py         # Publication quotidienne
│   ├── data/
│   │   └── bible_json/          # JSON depuis scrollmapper
│   └── main.py
├── .env
├── requirements.txt
└── docker-compose.yml
```

> 💡 **Note** : Conformément au cahier technique, **aucune authentification** n’est requise. Tous les contenus sont **publics et versionnés**.

---

## 🗃️ 2. Modèles SQLAlchemy (PostgreSQL)

### ✅ `BibleTranslation`
```python
class BibleTranslation(Base):
    __tablename__ = "bible_translations"
    id = Column(String, primary_key=True)  # ex: "fraLSG"
    name = Column(String)                  # ex: "Louis Segond 1910"
    locale = Column(String)                # "fr", "ee", "en"
    license_status = Column(String)        # "public_domain", "restricted"
    allowed_text = Column(Boolean, default=True)
    allowed_offline = Column(Boolean, default=True)
    allowed_tts = Column(Boolean, default=True)
    share_max_verses = Column(Integer, nullable=True)  # 1–3 si licence limitée
    attribution_text = Column(Text, nullable=True)
    source_reference = Column(String)
```

### ✅ `BibleBook`
```python
class BibleBook(Base):
    __tablename__ = "bible_books"
    id = Column(Integer, primary_key=True)
    translation_id = Column(String, ForeignKey("bible_translations.id"))
    name = Column(String)                  # ex: "Genèse"
    book_order = Column(Integer)           # 1 = Genèse, 66 = Apocalypse
```

### ✅ `BibleVerse`
```python
class BibleVerse(Base):
    __tablename__ = "bible_verses"
    id = Column(Integer, primary_key=True)
    translation_id = Column(String, ForeignKey("bible_translations.id"))
    book_id = Column(Integer, ForeignKey("bible_books.id"))
    chapter = Column(Integer)
    verse = Column(Integer)
    text = Column(Text)
    __table_args__ = (
        UniqueConstraint('translation_id', 'book_id', 'chapter', 'verse'),
    )
```

### ✅ `DailyContent`
```python
class DailyContent(Base):
    __tablename__ = "daily_content"
    id = Column(Integer, primary_key=True)
    date = Column(Date, index=True)               # ex: 2025-12-29
    translation_id = Column(String)
    book_id = Column(Integer)
    chapter = Column(Integer)
    verse_start = Column(Integer)
    verse_end = Column(Integer, default=None)     # pour plage de versets
    theme_tags = Column(ARRAY(String))            # ["paix", "anxiété"]
    reflection_text = Column(Text, nullable=True)  # IA ou rédaction interne
    source = Column(String, default="curated")    # "curated" ou "ai"
```

### ✅ `CrossReference` *(de openbible.info)*
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
    votes = Column(Integer, default=0)  # pertinence
```

---

## 🔁 3. Workflow de Chargement des Données

### Étape 1 : Récupérer les JSON
```bash
# app/data/bible_json/
wget https://github.com/scrollmapper/bible_databases/raw/2025/Formats/json/fraLSG.json
wget https://github.com/scrollmapper/bible_databases/raw/2025/Formats/json/eeb1983.json
wget https://github.com/scrollmapper/bible_databases/raw/2025/Formats/json/engWEB.json
```

### Étape 2 : Script de chargement (`bible_loader.py`)
```python
def load_bible_json(translation_id: str, json_path: str):
    # 1. Insérer traduction dans bible_translations
    db.add(BibleTranslation(
        id=translation_id,
        name="Louis Segond 1910",
        locale="fr",
        license_status="public_domain",
        allowed_offline=True,
        allowed_tts=True
    ))

    # 2. Charger JSON
    with open(json_path) as f:
        data = json.load(f)

    book_order = 1
    for book_name, chapters in data.items():
        # 3. Insérer livre
        book = BibleBook(
            translation_id=translation_id,
            name=book_name,
            book_order=book_order
        )
        db.add(book)
        db.flush()

        # 4. Insérer versets
        for chap_str, verses in chapters.items():
            chap_num = int(chap_str)
            for verse_str, text in verses.items():
                verse = BibleVerse(
                    translation_id=translation_id,
                    book_id=book.id,
                    chapter=chap_num,
                    verse=int(verse_str),
                    text=text.strip()
                )
                db.add(verse)
        book_order += 1
    db.commit()
```

> ✅ Idempotent, gère les doublons via `UniqueConstraint`.

---

## 🤖 4. Workflow d’IA **Responsable** (RAG)

Conformément au cahier technique, **l’IA ne génère pas de versets**, elle **sélectionne** parmi un corpus autorisé.

### Étape 1 : Indexation sémantique (facultatif, pour MVP : tags manuels)
- On associe chaque verset à des **tags** via règles simples :
  ```python
  # Exemple de mapping manuel (ou ML léger)
  verse_tags = {
      "anxiété": ["Matthieu 6:34", "Philippiens 4:6"],
      "paix": ["Jean 14:27", "Psaume 29:11"],
      "gratitude": ["1 Thessaloniciens 5:18"]
  }
  ```

### Étape 2 : Sélection IA (`ai_selector.py`)
```python
def select_verse_for_mood(mood: str, translation_id: str = "fraLSG"):
    # 1. Trouver candidats par tag
    candidates = db.query(BibleVerse).join(BibleBook).filter(
        BibleVerse.translation_id == translation_id,
        BibleBook.name.in_(verse_tags.get(mood, []))
    ).all()

    if not candidates:
        # Fallback : verset aléatoire du jour (curated)
        return get_curated_daily_verse(translation_id)

    # 2. Choisir via heuristique (ex: le plus court)
    selected = min(candidates, key=lambda v: len(v.text))

    # 3. Générer réflexion (avec prompt strict)
    reflection = gemini_generate_reflection(selected.text, mood)

    return selected, reflection
```

### Prompt IA strict (conforme au cahier)
```text
Tu es un assistant spirituel chrétien bienveillant.
À partir du verset suivant :
« {verse_text} »
Écris une **courte réflexion de 1–2 phrases** en français clair pour quelqu’un qui se sent {mood}.
Ne donne aucun conseil médical, financier ou prophétique.
Sois encourageant, humble et ancré dans la Parole.
```

> 🔒 **Sécurité** : sortie filtrée, IA désactivable, journal local-only par défaut.

---

## 📅 5. Envoi Quotidien du Verset

### Mécanisme : Tâche planifiée (`scheduler.py`)
- Utilise **Celery + Redis** ou **APScheduler**
- S’exécute **une fois par jour à 00h00 UTC** (normalisé)

### Logique :
```python
def publish_daily_content_for_date(target_date: date):
    for translation in ["fraLSG", "eeb1983", "engWEB"]:
        # Option 1 : contenu rédigé à l’avance
        curated = get_curated_verse_for_date(target_date, translation)
        if curated:
            save_to_daily_content(curated)
            continue

        # Option 2 : IA (si opt-in activé)
        if ai_enabled_for_translation(translation):
            verse, reflection = select_verse_for_mood("neutre", translation)
            save_to_daily_content({
                "date": target_date,
                "translation_id": translation,
                "book_id": verse.book_id,
                "chapter": verse.chapter,
                "verse_start": verse.verse,
                "reflection_text": reflection,
                "source": "ai"
            })
```

> 📌 **Important** : Aucun envoi push → l’appli **récupère le contenu via API** au démarrage.

---

## 🌐 6. Endpoints API (FastAPI)

| Endpoint | Méthode | Description |
|--------|--------|------------|
| `GET /v1/meta/version` | `GET` | Version globale du contenu (`2025.12.29`) |
| `GET /v1/translations?lang=fr` | `GET` | Liste traductions disponibles |
| `GET /v1/daily?date=2025-12-29&lang=fr&translation_id=fraLSG` | `GET` | Verset du jour |
| `GET /v1/verse/{book_id}/{chapter}/{verse}` | `GET` | Lire un verset |
| `GET /v1/cross-references?book=Jean&chapter=3&verse=16` | `GET` | Références croisées |

> ✅ **Tous les endpoints sont publics**, sans auth.

---

## 🔐 7. Gestion des Licences

- Chaque traduction a un statut dans `BibleTranslation`
- L’API vérifie avant de :
  - Autoriser le TTS → `if translation.allowed_tts`
  - Limiter le partage → `if shared_verses > translation.share_max_verses`
- Attribution incluse dans la réponse si nécessaire :
  ```json
  {
    "verse": "Car Dieu a tant aimé le monde...",
    "attribution": "Louis Segond 1910 – Domaine public"
  }
  ```

---

## 📦 8. Déploiement (Docker Compose)

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://soulverse:pwd@db/soulverse
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on: [db]

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: soulverse
      POSTGRES_USER: soulverse
    volumes: [./pgdata:/var/lib/postgresql/data]

  # Redis optionnel (si Celery)
```

---

## 💡 9. Fonctionnalités Anticipées (Conformes au Cahier)

| Fonction | Implémentation |
|--------|---------------|
| **Offline-first** | L’appli télécharge `daily_content` + `bible_verses` pour 7 jours |
| **Sans compte** | Toutes les données sont publiques ou stockées localement (Flutter) |
| **Respect licence** | Contrôle via `BibleTranslation` |
| **IA désactivable** | Flag dans metadata (`ai_enabled: false`) |
| **Multi-langue** | `lang=fr|ee|en` dans tous les endpoints |
| **Références croisées** | Via table `cross_references` |
| **Mise à jour delta** | `ETag` ou `version` dans les réponses |

---

## ✅ Avantages Clés

- **Zéro dépendance** à des API externes critiques (Bible en local)
- **Conforme** au cahier technique (sans compte, offline-first)
- **Évolutif** : ajout de traductions = nouveau JSON + `load_bible_json()`
- **Éthique** : IA encadrée, licence respectée, pas de tracking

---

> 🚀 **Prochaine étape** :  
> Veux-tu que je te génère :
> - Le script complet de `bible_loader.py` ?
> - Un exemple de réponse JSON pour `/v1/daily` ?
> - La configuration Traefik + Let’s Encrypt pour ton serveur à Lomé ?

Dis-moi !
