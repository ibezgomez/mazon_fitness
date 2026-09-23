"""Endpoints de autenticación: registro y login."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Trainer
from ..schemas import Token, TrainerCreate, TrainerOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TrainerOut, status_code=status.HTTP_201_CREATED)
def signup(data: TrainerCreate, db: Session = Depends(get_db)) -> Trainer:
    existe = db.execute(
        select(Trainer).where(Trainer.email == data.email)
    ).scalar_one_or_none()
    if existe is not None:
        raise HTTPException(status_code=400, detail="Ese email ya está registrado")

    trainer = Trainer(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(trainer)
    db.flush()
    return trainer


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    # OAuth2 usa el campo 'username'; aquí es el email.
    trainer = db.execute(
        select(Trainer).where(Trainer.email == form.username)
    ).scalar_one_or_none()
    if trainer is None or not verify_password(form.password, trainer.password_hash):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    return Token(access_token=create_access_token(str(trainer.id)))
