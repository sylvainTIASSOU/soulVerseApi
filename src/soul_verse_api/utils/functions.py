from src.soul_verse_api.core.config import settings

def is_development_environment() -> bool:
    return settings.ENVIRONMENT in ("development", "dev", "local")
