"""CRUD de recetas de biblioteca (con sus ingredientes). Aislado por tenant."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..deps import get_current_trainer, get_db
from ..models import Alimento, Receta, RecetaIngrediente, Trainer
from ..schemas import (
    Macros,
    RecetaCreate,
    RecetaIngredienteIn,
    RecetaIngredienteOut,
    RecetaOut,
    RecetaUpdate,
)
from ..services.meal_service import macros_de_receta

router = APIRouter(prefix="/recetas", tags=["recetas"])


def _validar_alimentos(db: Session, ingredientes: list[RecetaIngredienteIn]) -> None:
    ids = {i.alimento_id for i in ingredientes}
    encontrados = set(
        db.execute(select(Alimento.id).where(Alimento.id.in_(ids))).scalars().all()
    )
    faltan = ids - encontrados
    if faltan:
        raise HTTPException(
            status_code=400,
            detail=f"Estos alimentos no existen o no son tuyos: {sorted(str(x) for x in faltan)}",
        )


def _to_out(receta: Receta) -> RecetaOut:
    return RecetaOut(
        id=receta.id,
        nombre=receta.nombre,
        foto_url=receta.foto_url,
        instrucciones=receta.instrucciones,
        ingredientes=[RecetaIngredienteOut.model_validate(i) for i in receta.ingredientes],
        macros=Macros(**macros_de_receta(receta)),
    )


def _cargar(db: Session, receta_id: uuid.UUID) -> Receta:
    receta = db.execute(
        select(Receta)
        .where(Receta.id == receta_id)
        .options(selectinload(Receta.ingredientes).selectinload(RecetaIngrediente.alimento))
    ).scalar_one_or_none()
    if receta is None:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return receta


@router.post("", response_model=RecetaOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: RecetaCreate,
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> RecetaOut:
    _validar_alimentos(db, data.ingredientes)
    receta = Receta(
        tenant_id=trainer.id,
        nombre=data.nombre,
        foto_url=data.foto_url,
        instrucciones=data.instrucciones,
    )
    for ing in data.ingredientes:
        receta.ingredientes.append(RecetaIngrediente(
            tenant_id=trainer.id,
            alimento_id=ing.alimento_id,
            cantidad_base=ing.cantidad_base,
            fijo=ing.fijo,
            min_qty=ing.min_qty,
            max_qty=ing.max_qty,
        ))
    db.add(receta)
    db.flush()
    return _to_out(_cargar(db, receta.id))


@router.get("", response_model=list[RecetaOut])
def listar(
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> list[RecetaOut]:
    recetas = db.execute(
        select(Receta)
        .order_by(Receta.nombre)
        .options(selectinload(Receta.ingredientes).selectinload(RecetaIngrediente.alimento))
    ).scalars().all()
    return [_to_out(r) for r in recetas]


@router.get("/{receta_id}", response_model=RecetaOut)
def obtener(
    receta_id: uuid.UUID,
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> RecetaOut:
    return _to_out(_cargar(db, receta_id))


@router.put("/{receta_id}", response_model=RecetaOut)
def actualizar(
    receta_id: uuid.UUID,
    data: RecetaUpdate,
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> RecetaOut:
    receta = _cargar(db, receta_id)
    if data.nombre is not None:
        receta.nombre = data.nombre
    if data.foto_url is not None:
        receta.foto_url = data.foto_url
    if data.instrucciones is not None:
        receta.instrucciones = data.instrucciones
    if data.ingredientes is not None:
        _validar_alimentos(db, data.ingredientes)
        receta.ingredientes.clear()
        for ing in data.ingredientes:
            receta.ingredientes.append(RecetaIngrediente(
                tenant_id=trainer.id,
                alimento_id=ing.alimento_id,
                cantidad_base=ing.cantidad_base,
                fijo=ing.fijo,
                min_qty=ing.min_qty,
                max_qty=ing.max_qty,
            ))
    db.flush()
    return _to_out(_cargar(db, receta.id))


@router.delete("/{receta_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(
    receta_id: uuid.UUID,
    trainer: Trainer = Depends(get_current_trainer),
    db: Session = Depends(get_db),
) -> None:
    receta = _cargar(db, receta_id)
    db.delete(receta)
    db.flush()
