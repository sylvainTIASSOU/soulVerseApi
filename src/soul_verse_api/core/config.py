from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # use Pydantic v2 style Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    DATABASE_URL: str = ""
    # API Configuration
    API_V1_STR: str = "/api/v1"
    API_VERSION: str = "1.0.0"
    PROJECT_NAME: str = "SoulVerse API"

    # Redis Configuration
    REDIS_HOST: str = "redis://localhost:6379/0"
    REDIS_PORT: int = 6379

    # Gemini AI Configuration
    GEMINI_API_KEY: str = ""

    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_PRIVATE_KEY: str = ""
    FIREBASE_CLIENT_EMAIL: str = ""

    # Bible Configuration
    DEFAULT_TRANSLATION: str = "FreBBB"
    ENVIRONMENT: str = "production"


settings = Settings()
