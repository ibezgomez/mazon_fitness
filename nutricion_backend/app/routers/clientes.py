"""CRUD de clientes (del entrenador). Aislado por tenant vía RLS.

Nota: por ahora el cliente guarda lo mínimo (nombre + objetivo). El formulario
de alta completo (anamnesis: datos personales, cuadro clínico, etc.) es una fase
aparte más grande.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_trainer, get_db
from ..models import Cliente, Dieta, Trainer
from ..schemas import ClienteCreate, ClienteOut, ClienteUpdate, DietaOut

router = APIRouter(prefix="/clientes", tags=["clientes"])


def _get_own_or_404(db: Session, cliente_id: uuid.UUID) -> Cliente:
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def crear(data: ClienteCreate, trainer: Trainer = Depends(get_current_trainer),
          db: Session = Depends(get_db)) -> Cliente:
    cliente = Cliente(tenant_id=trainer.id, **data.model_dump())
    db.add(cliente)
    db.flush()
    return cliente


@router.get("", response_model=list[ClienteOut])
def listar(trainer: Trainer = Depends(get_current_trainer),
           db: Session = Depends(get_db)) -> list[Cliente]:
    return list(db.execute(select(Cliente).order_by(Cliente.nombre)).scalars().all())


@router.get("/{cliente_id}", response_model=ClienteOut)
def obtener(cliente_id: uuid.UUID, trainer: Trainer = Depends(get_current_trainer),
            db: Session = Depends(get_db)) -> Cliente:
    return _get_own_or_404(db, cliente_id)


@router.put("/{cliente_id}", response_model=ClienteOut)
def actualizar(cliente_id: uuid.UUID, data: ClienteUpdate,
               trainer: Trainer = Depends(get_current_trainer),
               db: Session = Depends(get_db)) -> Cliente:
    cliente = _get_own_or_404(db, cliente_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    db.flush()
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(cliente_id: uuid.UUID, trainer: Trainer = Depends(get_current_trainer),
           db: Session = Depends(get_db)) -> None:
    cliente = _get_own_or_404(db, cliente_id)
    db.delete(cliente)
    db.flush()


@router.get("/{cliente_id}/dietas", response_model=list[DietaOut])
def dietas_del_cliente(cliente_id: uuid.UUID,
                       trainer: Trainer = Depends(get_current_trainer),
                       db: Session = Depends(get_db)) -> list[Dieta]:
    _get_own_or_404(db, cliente_id)
    return list(
        db.execute(
            select(Dieta).where(Dieta.cliente_id == cliente_id).order_by(Dieta.nombre)
        ).scalars().all()
    )
