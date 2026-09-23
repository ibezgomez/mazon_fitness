"""Puente entre el ORM y el motor de macros.

- instanciar_receta_en_opcion: copia los ingredientes de una receta de
  biblioteca a una opción de comida (para "añadir" o "cambiar" receta).
- previsualizar_ajuste: calcula el ajuste SIN guardar.
- aplicar_ajuste: calcula y GUARDA las cantidades ajustadas + macros resultantes.
- macros_de_receta: suma los macros de una receta a partir de sus ingredientes.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Alimento, ComidaOpcion, OpcionIngrediente, Receta
from .macro_engine import Ingredient, RecipeItem, Target, Result, adjust_recipe


def _to_ingredient(alimento: Alimento) -> Ingredient:
    return Ingredient(
        name=alimento.nombre,
        kcal=alimento.kcal,
        protein=alimento.prote,
        carbs=alimento.carbs,
        fat=alimento.grasa,
        per_unit=(alimento.tipo == "unidad"),
    )


def _coef(alimento: Alimento, macro: str) -> float:
    val = getattr(alimento, macro)
    return val if alimento.tipo == "unidad" else val / 100.0


def macros_de_receta(receta: Receta) -> dict[str, float]:
    """Suma los macros de una receta a partir de sus ingredientes (cantidad base)."""
    campos = {"kcal": "kcal", "prote": "prote", "carbs": "carbs", "grasa": "grasa"}
    total = {k: 0.0 for k in campos}
    for ing in receta.ingredientes:
        for out_key, alim_attr in campos.items():
            total[out_key] += _coef(ing.alimento, alim_attr) * ing.cantidad_base
    return {k: round(v, 1) for k, v in total.items()}


def instanciar_receta_en_opcion(
    session: Session, opcion: ComidaOpcion, receta: Receta
) -> None:
    """Copia los ingredientes de una receta a una opción (reemplaza los actuales).

    Sirve tanto para añadir una receta a una comida como para 'cambiar la receta'.
    No ajusta todavía: eso lo hacen previsualizar_ajuste / aplicar_ajuste.
    """
    if receta.tenant_id != opcion.tenant_id:
        raise ValueError("La receta y la opción son de tenants distintos.")

    opcion.ingredientes.clear()
    opcion.receta_id = receta.id
    for ing in receta.ingredientes:
        opcion.ingredientes.append(
            OpcionIngrediente(
                tenant_id=opcion.tenant_id,
                alimento_id=ing.alimento_id,
                cantidad=ing.cantidad_base,
                fijo=ing.fijo,
                min_qty=ing.min_qty,
                max_qty=ing.max_qty,
            )
        )
    session.flush()


def _cargar_opcion(session: Session, opcion_id: uuid.UUID) -> ComidaOpcion:
    opcion = session.execute(
        select(ComidaOpcion)
        .where(ComidaOpcion.id == opcion_id)
        .options(
            selectinload(ComidaOpcion.ingredientes).selectinload(
                OpcionIngrediente.alimento
            ),
            selectinload(ComidaOpcion.comida),
        )
    ).scalar_one_or_none()
    if opcion is None:
        raise ValueError(f"No existe la opción {opcion_id}.")
    if not opcion.ingredientes:
        raise ValueError("La opción no tiene ingredientes que ajustar.")
    return opcion


def _resolver(opcion: ComidaOpcion) -> tuple[Result, dict[str, OpcionIngrediente]]:
    comida = opcion.comida
    target = Target(
        kcal=comida.obj_kcal,
        protein=comida.obj_prote,
        carbs=comida.obj_carbs,
        fat=comida.obj_grasa,
    )
    items: list[RecipeItem] = []
    linea_por_nombre: dict[str, OpcionIngrediente] = {}
    for linea in opcion.ingredientes:
        ing = _to_ingredient(linea.alimento)
        items.append(RecipeItem(
            ingredient=ing, base_qty=linea.cantidad,
            fixed=linea.fijo, min_qty=linea.min_qty, max_qty=linea.max_qty,
        ))
        linea_por_nombre[ing.name] = linea
    return adjust_recipe(items, target), linea_por_nombre


def previsualizar_ajuste(session: Session, opcion_id: uuid.UUID) -> Result:
    """Calcula el ajuste y lo devuelve SIN tocar la base de datos."""
    opcion = _cargar_opcion(session, opcion_id)
    res, _ = _resolver(opcion)
    if not res.feasible:
        raise RuntimeError(res.message)
    return res


def aplicar_ajuste(session: Session, opcion_id: uuid.UUID) -> Result:
    """Calcula el ajuste y GUARDA las cantidades + los macros resultantes."""
    opcion = _cargar_opcion(session, opcion_id)
    res, linea_por_nombre = _resolver(opcion)
    if not res.feasible:
        raise RuntimeError(res.message)

    for nombre, cantidad in res.quantities.items():
        linea_por_nombre[nombre].cantidad = cantidad
    opcion.res_kcal = res.totals["kcal"]
    opcion.res_prote = res.totals["protein"]
    opcion.res_carbs = res.totals["carbs"]
    opcion.res_grasa = res.totals["fat"]
    session.flush()
    return res
