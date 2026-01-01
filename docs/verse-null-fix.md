# Fix: Champ "verse" retourne null

## 🐛 Problème
Le verset quotidien généré retourne toujours `"verse": null` même si l'IA génère une référence correcte.

## 🔍 Analyse
```json
{
  "verse": null,  // ❌ Toujours null
  "ai_response": {
    "reference": "Jérémie 29:11",  // ✅ Référence correcte
    "reflection": "..."
  },
  "has_full_verse": false  // ❌ Indique que le verset n'a pas été trouvé
}
```

## 💡 Causes identifiées

### 1. **Mapping des noms de livres**
Le nom du livre dans la référence (ex: "Jérémie") ne correspondait pas exactement au nom dans la base de données JSON de la Bible.

**Problème:** 
- IA renvoie: "Jérémie 29:11"
- Base de données attend: "Jérémie" (exact match case-insensitive)

**Solution:**
Ajout d'un dictionnaire de mapping avec toutes les variantes possibles:
```python
self.book_name_mapping = {
    "jérémie": "Jérémie",
    "jeremie": "Jérémie",
    # ... autres variantes
}
```

### 2. **Logs insuffisants**
Il était difficile de diagnostiquer où le parsing échouait.

**Solution:**
Ajout de logs détaillés à chaque étape:
```python
logger.info(f"🔍 Parsing référence: '{reference}'")
logger.info(f"📖 Livre: '{book}', Chapitre:verset: '{chapter_verse_part}'")
logger.info(f"📍 Recherche: {book} {chapter}:{verse_num}")
```

## 🔧 Corrections appliquées

### 1. **bible_service.py**

#### Ajout de normalize_book_name()
```python
def normalize_book_name(self, book: str) -> str:
    """
    Normalise le nom d'un livre biblique
    Exemple: "Jérémie" → "Jérémie", "jeremie" → "Jérémie"
    """
    book_lower = book.lower().strip()
    return self.book_name_mapping.get(book_lower, book)
```

#### Amélioration de get_verse()
```python
async def get_verse(self, translation: str, book: str, chapter: int, verse: int):
    # Normaliser le nom du livre
    normalized_book = self.normalize_book_name(book)
    logger.info(f"📖 Recherche: '{book}' → '{normalized_book}' {chapter}:{verse}")
    
    # Recherche avec normalisation
    for bible_book in bible_data.get("books", []):
        if bible_book["name"].lower() == normalized_book.lower():
            # ... recherche chapitre et verset
            
    # Si pas trouvé, logger les livres disponibles
    available_books = [b["name"] for b in bible_data.get("books", [])]
    logger.warning(f"❌ Livre '{normalized_book}' non trouvé. Disponibles: {available_books[:10]}...")
```

### 2. **scheduler_service.py**

#### Amélioration du parsing de référence
```python
# Avant
ref_parts = ai_response["reference"].strip().split()

# Après (avec logs détaillés)
reference = ai_response["reference"].strip()
logger.info(f"🔍 Parsing référence: '{reference}'")

ref_parts = reference.split()
chapter_verse_part = ref_parts[-1]
book = " ".join(ref_parts[:-1])

logger.info(f"📖 Livre: '{book}', Partie: '{chapter_verse_part}'")

# Conversion avec gestion d'erreur explicite
try:
    chapter = int(chapter_verse[0])
    verse_num = int(chapter_verse[1])
    logger.info(f"📍 Recherche: {book} {chapter}:{verse_num}")
except ValueError as ve:
    logger.warning(f"❌ Erreur conversion nombres: {ve}")
```

## 📖 Mapping des livres bibliques

### Ancien Testament
- Genèse, Exode, Lévitique, Nombres, Deutéronome
- Josué, Juges, Ruth
- I Samuel, II Samuel, I Rois, II Rois
- **Jérémie** (avec variantes: jeremie, jérémie)
- Ésaïe (avec variantes: esaïe, isaïe)
- Ézéchiel (avec variantes: ezéchiel)
- Psaumes (avec variantes: psaume, psaumes)

### Nouveau Testament
- Matthieu, Marc, Luc, Jean
- Actes (avec variante: Actes des Apôtres)
- Romains, I Corinthiens, II Corinthiens
- Galates, Éphésiens, Philippiens, Colossiens
- I Thessaloniciens, II Thessaloniciens
- I Timothée, II Timothée, Tite, Philémon
- Hébreux, Jacques, I Pierre, II Pierre
- I Jean, II Jean, III Jean, Jude, Apocalypse

## 🧪 Test

Pour tester si le fix fonctionne, regarder les logs lors de la génération:

```
INFO:🔍 Parsing référence: 'Jérémie 29:11'
INFO:📖 Livre: 'Jérémie', Partie chapitre:verset: '29:11'
INFO:📍 Recherche: Jérémie 29:11
INFO:📖 Recherche: 'Jérémie' → 'Jérémie' 29:11
INFO:✅ Livre trouvé: Jérémie
INFO:✅ Verset trouvé: Car je connais les projets que...
```

Si le verset est trouvé, la réponse devrait contenir:
```json
{
  "verse": {
    "book": "Jérémie",
    "chapter": 29,
    "verse": 11,
    "text": "Car je connais les projets que j'ai formés sur vous...",
    "translation": "FreBBB"
  },
  "has_full_verse": true
}
```

## ✅ Validation

Vérifier que:
1. ✅ Les logs montrent le parsing étape par étape
2. ✅ Le nom du livre est normalisé correctement
3. ✅ Le verset est trouvé dans la base de données
4. ✅ Le champ `"verse"` n'est plus `null`
5. ✅ Le champ `"has_full_verse"` est `true`

## 🚀 Prochaines étapes

Si le problème persiste:
1. Vérifier les logs pour voir à quelle étape ça échoue
2. Vérifier le format exact des noms de livres dans la base JSON
3. Ajouter plus de variantes dans le mapping si nécessaire
4. Tester avec différentes références (AT et NT)
