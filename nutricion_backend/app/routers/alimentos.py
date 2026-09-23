"""CRUD de alimentos. Todo queda aislado por tenant gracias al RLS:
get_current_trainer fija el tenant, así que estas consultas solo ven/afectan
a los alimentos del entrenador autenticado.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_trainer, get_db
from ..models import Alimento, Trainer
from ..schemas import AlimentoCreate, AlimentoOut, AlimentoUpdate

router = APIRouter(prefix="/alimentos", tags=["alimentos"])


def _get_own_or_404(db: Session, alimento_id: uuid.UUID) -> Alimento:
    # RLS hace que db.get devuelva None si el alimento es de otro tenant.
    alimento = db.get(Alimento, alimento_id)
    if alimento is None:
        raise HTTPException(status_code=404, detail="Alimento no encontrado")
    return alimento


@router.post("", response_model=AlimentoOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: AlimentoCreate,
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> Alimento:
    alimento = Alimento(tenant_id=trainer.id, **data.model_dump())
    db.add(alimento)
    db.flush()
    return alimento


@router.get("", response_model=list[AlimentoOut])
def listar(
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> list[Alimento]:
    return list(
        db.execute(select(Alimento).order_by(Alimento.nombre)).scalars().all()
    )


@router.get("/{alimento_id}", response_model=AlimentoOut)
def obtener(
    alimento_id: uuid.UUID,
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> Alimento:
    return _get_own_or_404(db, alimento_id)


@router.put("/{alimento_id}", response_model=AlimentoOut)
def actualizar(
    alimento_id: uuid.UUID,
    data: AlimentoUpdate,
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> Alimento:
    alimento = _get_own_or_404(db, alimento_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(alimento, campo, valor)
    db.flush()
    return alimento


@router.delete("/{alimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(
    alimento_id: uuid.UUID,
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> None:
    alimento = _get_own_or_404(db, alimento_id)
    db.delete(alimento)
    db.flush()
