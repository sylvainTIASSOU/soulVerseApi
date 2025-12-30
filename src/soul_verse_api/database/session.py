from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.soul_verse_api.core.config import settings
from src.soul_verse_api.utils.functions import is_development_environment

if is_development_environment():
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("SQLALCHEMY_DATABASE_URL n'est pas défini")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
