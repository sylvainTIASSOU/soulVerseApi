from src.soul_verse_api.api.v1 import user
from src.soul_verse_api.database.session import Base, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.soul_verse_api.core.config import settings

from src.soul_verse_api.core.redis_client import redis_client
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
    """Créer le bucket au démarrage de l'API."""
    # create_bucket_if_not_exists(settings.MINIO_BUCKET)
    print("🚀 Démarrage de l'API======================")
    redis_client.connect()
    # yield
    # redis_client.disconnect()

Base.metadata.create_all(bind=engine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
    }


app.include_router(router=user.router, prefix="/api/v1")