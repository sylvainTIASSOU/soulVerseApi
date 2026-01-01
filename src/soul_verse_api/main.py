from src.soul_verse_api.api.v1 import user
from src.soul_verse_api.api.v1 import verses
from src.soul_verse_api.api.v1 import scheduler
from src.soul_verse_api.api.v1 import prayers
from src.soul_verse_api.database.session import Base, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from src.soul_verse_api.core.config import settings

from src.soul_verse_api.core.redis_client import redis_client
from src.soul_verse_api.services.scheduler_service import scheduler_service
from src.soul_verse_api.utils.functions import is_development_environment

app = FastAPI(
    root_path=settings.API_V1_STR,
    debug=is_development_environment(),
    title=settings.PROJECT_NAME,
    description="API pour SoulVerse - L'application de méditation biblique alimentée par l'IA",
    version=settings.API_VERSION,
    docs_url="/docs" if is_development_environment() else None,
    redoc_url="/redoc" if is_development_environment() else None,
    openapi_url="/openapi.json" if is_development_environment() else None,
    swagger_ui_parameters={
        "syntaxHighlight": {"theme": "obsidian"},
        "persistAuthorization": True,
        "displayRequestDuration": True,
    },
)


@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage de l'API."""
    print("🚀 Démarrage de SoulVerse API======================")

    # Connexion à Redis
    try:
        redis_client.connect()
        if redis_client.is_connected():
            print("✅ Redis connecté avec succès")
        else:
            print("⚠️ Redis non connecté - mode dégradé")
    except Exception as e:
        print(f"❌ Erreur connexion Redis: {e}")

    # Démarrage du planificateur
    try:
        scheduler_service.start()
        print("✅ Planificateur de versets quotidiens démarré")
    except Exception as e:
        print(f"⚠️ Erreur démarrage planificateur: {e}")

    print("✅ SoulVerse API prête !")


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt de l'API."""
    print("🛑 Arrêt de SoulVerse API...")

    # Déconnexion Redis
    try:
        redis_client.disconnect()
        print("✅ Redis déconnecté proprement")
    except Exception as e:
        print(f"⚠️ Erreur déconnexion Redis: {e}")

    # Arrêt du planificateur
    try:
        scheduler_service.stop()
        print("✅ Planificateur arrêté proprement")
    except Exception as e:
        print(f"⚠️ Erreur arrêt planificateur: {e}")

    print("👋 SoulVerse API arrêtée")

Base.metadata.create_all(bind=engine)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des fichiers statiques pour les images
static_dir = Path("storage/verse_images")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/verse_images",
          StaticFiles(directory=str(static_dir)), name="verse_images")


@app.get("/", tags=["system"])
async def root():
    return {
        "message": "🙏 Bienvenue sur SoulVerse API",
        "description": "API pour la méditation biblique alimentée par l'IA",
        "version": settings.API_VERSION,
        "docs": "/docs" if is_development_environment() else "Documentation désactivée en production"
    }


@app.get("/health", tags=["system"])
async def health():
    """Endpoint de santé de l'API"""
    redis_status = redis_client.is_connected() if redis_client else False

    return {
        "status": "healthy" if redis_status else "degraded",
        "service": "SoulVerse API",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "redis_connected": redis_status,
        "timestamp": "now"
    }


# Inclusion des routers
app.include_router(router=user.router)
app.include_router(router=verses.router)
app.include_router(router=scheduler.router)
app.include_router(router=prayers.router)
