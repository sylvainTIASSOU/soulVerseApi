# 📅 Service de Planification (SchedulerService)

Le `SchedulerService` gère la génération automatique des versets quotidiens et diverses tâches planifiées pour l'application SoulVerse.

## 🚀 Fonctionnalités

### ⏰ Jobs Planifiés Automatiques

1. **Versets Quotidiens** (6h00 - Africa/Lome)
   - Génère des versets personnalisés pour tous les utilisateurs actifs
   - Basé sur le mood de chaque utilisateur
   - Mise en cache Redis pour 2 heures

2. **Nettoyage Cache** (2h00 - Africa/Lome)
   - Supprime les caches expirés
   - Optimise les performances Redis

3. **Statistiques Utilisateurs** (00h00 - Africa/Lome)
   - Met à jour les statistiques d'activité
   - Comptabilise les utilisateurs actifs quotidiens

### 🔧 Gestion Base de Données

- **Récupération utilisateurs actifs** avec filtres
- **Session management** avec context managers
- **Gestion des fuseaux horaires** (Africa/Lome par défaut)

## 📡 API Endpoints

### Administration Scheduler

```bash
# Statut du planificateur
GET /api/v1/scheduler/status

# Démarrer le planificateur  
POST /api/v1/scheduler/start

# Arrêter le planificateur
POST /api/v1/scheduler/stop

# Health check
GET /api/v1/scheduler/health
```

### Déclenchement Manuel

```bash
# Générer versets quotidiens manuellement
POST /api/v1/scheduler/trigger-daily-verses

# Nombre d'utilisateurs actifs
GET /api/v1/scheduler/users-count
```

## 🔍 Exemples d'Utilisation

### Vérifier le Statut

```bash
curl http://localhost:8000/api/v1/scheduler/status
```

**Réponse :**
```json
{
  "running": true,
  "jobs_count": 3,
  "jobs": [
    {
      "id": "daily_verses_generation",
      "name": "Génération versets quotidiens",
      "next_run": "2025-12-31T06:00:00+00:00",
      "trigger": "cron[hour=6, minute=0]"
    }
  ],
  "timezone": "Africa/Lome",
  "status_checked_at": "2025-12-30T10:30:00"
}
```

### Déclencher Génération Manuelle

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/trigger-daily-verses
```

**Réponse :**
```json
{
  "success": true,
  "message": "Génération manuelle terminée avec succès",
  "triggered_at": "2025-12-30T10:30:00"
}
```

## 🛠️ Configuration Technique

### Variables d'Environnement

Aucune configuration spécifique requise - utilise les services existants :
- Redis pour le cache
- Base de données PostgreSQL pour les utilisateurs
- Gemini AI pour génération versets

### Dépendances

- `apscheduler` - Planification des tâches
- `sqlalchemy` - Base de données
- Services existants (Redis, Gemini, Bible)

## 🚨 Gestion d'Erreurs

### Stratégies de Fallback

1. **Échec IA Gemini** → Versets prédéfinis par mood
2. **Redis indisponible** → Continue sans cache
3. **DB indisponible** → Logs d'erreur + retry automatique

### Traitement par Batch

- **50 utilisateurs par batch** pour éviter surcharge
- **Pause 1 seconde** entre batches
- **Logs détaillés** succès/échecs

### Monitoring

```python
# Logs structurés
logger.info(f"✅ Génération terminée: {succès} succès, {erreurs} erreurs")

# Health check détaillé
GET /api/v1/scheduler/health
```

## 🔄 Intégration Application

### Démarrage Automatique

Le scheduler démarre automatiquement avec l'application :

```python
# main.py
@app.on_event("startup")
async def startup_event():
    # ... autres initialisations
    scheduler_service.start()
    print("✅ Planificateur de versets quotidiens démarré")
```

### Arrêt Propre

```python
# main.py  
@app.on_event("shutdown")
async def shutdown_event():
    # ... autres nettoyages
    scheduler_service.stop()
    print("✅ Planificateur arrêté proprement")
```

## 📊 Métriques & Performance

### Indicateurs Clés

- **Utilisateurs traités/min** : ~50 utilisateurs par batch
- **Taux de succès IA** : Fallback automatique si échec
- **Cache hit ratio** : Versets en cache = skip génération
- **Durée traitement** : Logs temporels détaillés

### Optimisations

- **Cache Redis** 2h pour versets quotidiens
- **Traitement asynchrone** avec asyncio.gather
- **Context managers** pour gestion DB
- **Batch processing** pour scalabilité

## 🔐 Sécurité

- **Validation utilisateurs actifs** (is_active=True + FCM token)
- **Gestion sessions DB** propre avec context managers
- **Logs sans données sensibles** (UUID tronqués)
- **Isolation des erreurs** par utilisateur

## 🚀 Roadmap

- [ ] **Notifications push** intégrées au scheduler
- [ ] **Métriques Prometheus** pour monitoring
- [ ] **Configuration dynamique** des horaires
- [ ] **Support multi-timezone** avancé
- [ ] **API webhooks** pour événements scheduler