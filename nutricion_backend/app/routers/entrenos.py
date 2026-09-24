"""Estructura de entrenamiento: rutina -> día -> ejercicio. Aislado por tenant."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..deps import get_current_trainer, get_db
from ..models import (
    Cliente,
    Ejercicio,
    Rutina,
    RutinaDia,
    RutinaEjercicio,
    Trainer,
)
from ..schemas import (
    RutinaCreate,
    RutinaDetalle,
    RutinaDiaCreate,
    RutinaDiaOut,
    RutinaEjercicioCreate,
    RutinaEjercicioOut,
    RutinaOut,
)

router = APIRouter(tags=["entrenamiento"])


def _get_or_404(db: Session, modelo, id_, nombre: str):
    obj = db.get(modelo, id_)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{nombre} no encontrado")
    return obj


@router.post("/rutinas", response_model=RutinaOut, status_code=201)
def crear_rutina(data: RutinaCreate, trainer: Trainer = Depends(get_current_trainer),
                 db: Session = Depends(get_db)) -> Rutina:
    if data.cliente_id is not None and db.get(Cliente, data.cliente_id) is None:
        raise HTTPException(status_code=400, detail="Ese cliente no existe o no es tuyo")
    rutina = Rutina(tenant_id=trainer.id, **data.model_dump())
    db.add(rutina)
    db.flush()
    return rutina


@router.get("/rutinas", response_model=list[RutinaOut])
def listar_rutinas(trainer: Trainer = Depends(get_current_trainer),
                   db: Session = Depends(get_db)) -> list[Rutina]:
    return list(db.execute(select(Rutina).order_by(Rutina.nombre)).scalars().all())


@router.get("/rutinas/{rutina_id}", response_model=RutinaDetalle)
def obtener_rutina(rutina_id: uuid.UUID, trainer: Trainer = Depends(get_current_trainer),
                   db: Session = Depends(get_db)) -> Rutina:
    rutina = db.execute(
        select(Rutina).where(Rutina.id == rutina_id).options(
            selectinload(Rutina.dias).selectinload(RutinaDia.ejercicios)
        )
    ).scalar_one_or_none()
    if rutina is None:
        raise HTTPException(status_code=404, detail="Rutina no encontrada")
    return rutina


@router.post("/rutinas/{rutina_id}/dias", response_model=RutinaDiaOut, status_code=201)
def crear_dia(rutina_id: uuid.UUID, data: RutinaDiaCreate,
              trainer: Trainer = Depends(get_current_trainer),
              db: Session = Depends(get_db)) -> RutinaDia:
    _get_or_404(db, Rutina, rutina_id, "Rutina")
    dia = RutinaDia(tenant_id=trainer.id, rutina_id=rutina_id, **data.model_dump())
    db.add(dia)
    db.flush()
    return dia


@router.post("/rutina-dias/{dia_id}/ejercicios", response_model=RutinaEjercicioOut, status_code=201)
def anadir_ejercicio(dia_id: uuid.UUID, data: RutinaEjercicioCreate,
                     trainer: Trainer = Depends(get_current_trainer),
                     db: Session = Depends(get_db)) -> RutinaEjercicio:
    _get_or_404(db, RutinaDia, dia_id, "Día")
    if db.get(Ejercicio, data.ejercicio_id) is None:
        raise HTTPException(status_code=400, detail="Ese ejercicio no existe o no es tuyo")
    re = RutinaEjercicio(tenant_id=trainer.id, rutina_dia_id=dia_id, **data.model_dump())
    db.add(re)
    db.flush()
    return re


@router.get("/clientes/{cliente_id}/rutinas", response_model=list[RutinaOut])
def rutinas_del_cliente(cliente_id: uuid.UUID,
                        trainer: Trainer = Depends(get_current_trainer),
                        db: Session = Depends(get_db)) -> list[Rutina]:
    _get_or_404(db, Cliente, cliente_id, "Cliente")
    return list(db.execute(
        select(Rutina).where(Rutina.cliente_id == cliente_id).order_by(Rutina.nombre)
    ).scalars().all())
