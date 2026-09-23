"""Dependencias compartidas de FastAPI."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session

from .db import SessionLocal, set_tenant
from .models import Trainer
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    """Abre una sesión por request; hace commit si todo va bien, rollback si no."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_trainer(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Trainer:
    """Valida el token, carga el entrenador y FIJA el tenant para esta request.

    A partir de aquí, todas las consultas del dominio quedan filtradas por RLS
    al tenant de este entrenador.
    """
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        trainer_id = uuid.UUID(decode_access_token(token))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise credenciales_invalidas

    trainer = db.get(Trainer, trainer_id)
    if trainer is None:
        raise credenciales_invalidas

    set_tenant(db, trainer.id)
    return trainer
