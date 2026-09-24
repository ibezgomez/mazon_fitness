"""CRUD de ejercicios de biblioteca. Aislado por tenant."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_trainer, get_db
from ..models import Ejercicio, Trainer
from ..schemas import EjercicioCreate, EjercicioOut, EjercicioUpdate

router = APIRouter(prefix="/ejercicios", tags=["ejercicios"])


def _get_own_or_404(db: Session, ejercicio_id: uuid.UUID) -> Ejercicio:
    ej = db.get(Ejercicio, ejercicio_id)
    if ej is None:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    return ej


@router.post("", response_model=EjercicioOut, status_code=status.HTTP_201_CREATED)
def crear(data: EjercicioCreate, trainer: Trainer = Depends(get_current_trainer),
          db: Session = Depends(get_db)) -> Ejercicio:
    ej = Ejercicio(tenant_id=trainer.id, **data.model_dump())
    db.add(ej)
    db.flush()
    return ej


@router.get("", response_model=list[EjercicioOut])
def listar(trainer: Trainer = Depends(get_current_trainer),
           db: Session = Depends(get_db)) -> list[Ejercicio]:
    return list(db.execute(select(Ejercicio).order_by(Ejercicio.nombre)).scalars().all())


@router.get("/{ejercicio_id}", response_model=EjercicioOut)
def obtener(ejercicio_id: uuid.UUID, trainer: Trainer = Depends(get_current_trainer),
            db: Session = Depends(get_db)) -> Ejercicio:
    return _get_own_or_404(db, ejercicio_id)


@router.put("/{ejercicio_id}", response_model=EjercicioOut)
def actualizar(ejercicio_id: uuid.UUID, data: EjercicioUpdate,
               trainer: Trainer = Depends(get_current_trainer),
               db: Session = Depends(get_db)) -> Ejercicio:
    ej = _get_own_or_404(db, ejercicio_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(ej, campo, valor)
    db.flush()
    return ej


@router.delete("/{ejercicio_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(ejercicio_id: uuid.UUID, trainer: Trainer = Depends(get_current_trainer),
           db: Session = Depends(get_db)) -> None:
    ej = _get_own_or_404(db, ejercicio_id)
    db.delete(ej)
    db.flush()
