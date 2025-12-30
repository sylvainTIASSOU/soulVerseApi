from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.soul_verse_api.models.Models import User
from src.soul_verse_api.schemas.user_schemas import UserCreate, User as UserSchema
from src.soul_verse_api.api.deps import get_db

router = APIRouter(prefix="/users", tags=["users management"])


@router.post("/", response_model=UserSchema)
async def create_user(payload: UserCreate,  db: Session = Depends(get_db)):
    """Créer un nouvel utilisateur"""
    new_user = User(
        fcm_token=payload.fcm_token,
        phone_model=payload.phone_model,
        phone_os=payload.phone_os,
        app_version=payload.app_version,
        phone_mark=payload.phone_mark,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
