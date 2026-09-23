"""Estructura del plan (dieta -> día -> comida -> opción) y ajuste de macros.

Incluye el endpoint estrella: previsualizar/aplicar el ajuste de una opción a
los macros objetivo de su comida (usa el motor de macros).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..deps import get_current_trainer, get_db
from ..models import (
    Cliente,
    Comida,
    ComidaOpcion,
    Dieta,
    DietaDia,
    OpcionIngrediente,
    Receta,
    RecetaIngrediente,
    Trainer,
)
from ..schemas import (
    AjusteOut,
    CambiarReceta,
    ComidaCreate,
    ComidaOut,
    DiaCreate,
    DiaOut,
    DietaCreate,
    DietaOut,
    OpcionCreate,
    OpcionOut,
)
from ..services import meal_service

router = APIRouter(tags=["planes"])


# --- helpers ---------------------------------------------------------------
def _get_or_404(db: Session, modelo, id_, nombre: str):
    obj = db.get(modelo, id_)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{nombre} no encontrado")
    return obj


def _cargar_receta(db: Session, receta_id: uuid.UUID) -> Receta:
    receta = db.execute(
        select(Receta)
        .where(Receta.id == receta_id)
        .options(selectinload(Receta.ingredientes))
    ).scalar_one_or_none()
    if receta is None:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return receta


def _cargar_opcion(db: Session, opcion_id: uuid.UUID) -> ComidaOpcion:
    opcion = db.execute(
        select(ComidaOpcion)
        .where(ComidaOpcion.id == opcion_id)
        .options(selectinload(ComidaOpcion.ingredientes))
    ).scalar_one_or_none()
    if opcion is None:
        raise HTTPException(status_code=404, detail="Opción no encontrada")
    return opcion


# --- dietas ----------------------------------------------------------------
@router.post("/dietas", response_model=DietaOut, status_code=201)
def crear_dieta(data: DietaCreate, trainer: Trainer = Depends(get_current_trainer),
                db: Session = Depends(get_db)) -> Dieta:
    if data.cliente_id is not None and db.get(Cliente, data.cliente_id) is None:
        raise HTTPException(status_code=400, detail="Ese cliente no existe o no es tuyo")
    dieta = Dieta(tenant_id=trainer.id, **data.model_dump())
    db.add(dieta)
    db.flush()
    return dieta


@router.get("/dietas", response_model=list[DietaOut])
def listar_dietas(trainer: Trainer = Depends(get_current_trainer),
                  db: Session = Depends(get_db)) -> list[Dieta]:
    return list(db.execute(select(Dieta).order_by(Dieta.nombre)).scalars().all())


@router.get("/dietas/{dieta_id}", response_model=DietaOut)
def obtener_dieta(dieta_id: uuid.UUID, trainer: Trainer = Depends(get_current_trainer),
                  db: Session = Depends(get_db)) -> Dieta:
    return _get_or_404(db, Dieta, dieta_id, "Dieta")


# --- días ------------------------------------------------------------------
@router.post("/dietas/{dieta_id}/dias", response_model=DiaOut, status_code=201)
def crear_dia(dieta_id: uuid.UUID, data: DiaCreate,
              trainer: Trainer = Depends(get_current_trainer),
              db: Session = Depends(get_db)) -> DietaDia:
    _get_or_404(db, Dieta, dieta_id, "Dieta")
    dia = DietaDia(tenant_id=trainer.id, dieta_id=dieta_id, **data.model_dump())
    db.add(dia)
    db.flush()
    return dia


# --- comidas ---------------------------------------------------------------
@router.post("/dias/{dia_id}/comidas", response_model=ComidaOut, status_code=201)
def crear_comida(dia_id: uuid.UUID, data: ComidaCreate,
                 trainer: Trainer = Depends(get_current_trainer),
                 db: Session = Depends(get_db)) -> Comida:
    _get_or_404(db, DietaDia, dia_id, "Día")
    comida = Comida(tenant_id=trainer.id, dieta_dia_id=dia_id, **data.model_dump())
    db.add(comida)
    db.flush()
    return _cargar_comida(db, comida.id)


def _cargar_comida(db: Session, comida_id: uuid.UUID) -> Comida:
    comida = db.execute(
        select(Comida)
        .where(Comida.id == comida_id)
        .options(selectinload(Comida.opciones).selectinload(ComidaOpcion.ingredientes))
    ).scalar_one_or_none()
    if comida is None:
        raise HTTPException(status_code=404, detail="Comida no encontrada")
    return comida


@router.get("/comidas/{comida_id}", response_model=ComidaOut)
def obtener_comida(comida_id: uuid.UUID, trainer: Trainer = Depends(get_current_trainer),
                   db: Session = Depends(get_db)) -> Comida:
    return _cargar_comida(db, comida_id)


# --- opciones (añadir / cambiar receta) ------------------------------------
@router.post("/comidas/{comida_id}/opciones", response_model=OpcionOut, status_code=201)
def anadir_opcion(comida_id: uuid.UUID, data: OpcionCreate,
                  trainer: Trainer = Depends(get_current_trainer),
                  db: Session = Depends(get_db)) -> ComidaOpcion:
    _get_or_404(db, Comida, comida_id, "Comida")
    receta = _cargar_receta(db, data.receta_id)
    opcion = ComidaOpcion(
        tenant_id=trainer.id, comida_id=comida_id, por_defecto=data.por_defecto
    )
    db.add(opcion)
    db.flush()
    meal_service.instanciar_receta_en_opcion(db, opcion, receta)
    return _cargar_opcion(db, opcion.id)


@router.put("/opciones/{opcion_id}/receta", response_model=OpcionOut)
def cambiar_receta(opcion_id: uuid.UUID, data: CambiarReceta,
                   trainer: Trainer = Depends(get_current_trainer),
                   db: Session = Depends(get_db)) -> ComidaOpcion:
    opcion = _cargar_opcion(db, opcion_id)
    receta = _cargar_receta(db, data.receta_id)
    meal_service.instanciar_receta_en_opcion(db, opcion, receta)
    return _cargar_opcion(db, opcion.id)


# --- ajuste de macros (previsualizar / aplicar) ----------------------------
@router.post("/opciones/{opcion_id}/previsualizar-ajuste", response_model=AjusteOut)
def previsualizar(opcion_id: uuid.UUID, trainer: Trainer = Depends(get_current_trainer),
                  db: Session = Depends(get_db)) -> AjusteOut:
    _get_or_404(db, ComidaOpcion, opcion_id, "Opción")
    try:
        res = meal_service.previsualizar_ajuste(db, opcion_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return AjusteOut(feasible=res.feasible, quantities=res.quantities, totals=res.totals,
                     target=res.target, deviations=res.deviations, within_margin=res.within_margin)


@router.post("/opciones/{opcion_id}/aplicar-ajuste", response_model=AjusteOut)
def aplicar(opcion_id: uuid.UUID, trainer: Trainer = Depends(get_current_trainer),
            db: Session = Depends(get_db)) -> AjusteOut:
    _get_or_404(db, ComidaOpcion, opcion_id, "Opción")
    try:
        res = meal_service.aplicar_ajuste(db, opcion_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return AjusteOut(feasible=res.feasible, quantities=res.quantities, totals=res.totals,
                     target=res.target, deviations=res.deviations, within_margin=res.within_margin)
