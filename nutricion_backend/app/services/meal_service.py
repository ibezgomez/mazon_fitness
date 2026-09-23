"""Puente entre el ORM y el motor de macros.

Coge una ComidaOpcion (sus ingredientes reales) y los objetivos de su Comida,
llama al motor y guarda las cantidades ajustadas de vuelta en cada
OpcionIngrediente, más los macros resultantes en la propia opción.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import (
    Alimento,
    Comida,
    ComidaOpcion,
    OpcionIngrediente,
    Receta,
)
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


def instanciar_receta_en_opcion(
    session: Session, opcion: ComidaOpcion, receta: Receta
) -> None:
    """Copia los ingredientes de una receta de biblioteca a una opción.

    Sustituye por completo los ingredientes actuales de la opción (útil para
    'cambiar una receta'). No ajusta todavía: eso lo hace `ajustar_opcion`.
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


def ajustar_opcion(session: Session, opcion_id: uuid.UUID) -> Result:
    """Ajusta las cantidades de una opción a los macros objetivo de su comida.

    Lee la opción y su comida, llama al motor, y persiste las cantidades
    ajustadas y los macros resultantes. Devuelve el Result del motor (incluye
    qué macros quedaron dentro de margen).
    """
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

    comida: Comida = opcion.comida
    target = Target(
        kcal=comida.obj_kcal,
        protein=comida.obj_prote,
        carbs=comida.obj_carbs,
        fat=comida.obj_grasa,
    )

    # Mapear líneas ORM -> items del motor, guardando la referencia inversa
    # (por nombre de alimento) para escribir de vuelta la cantidad ajustada.
    items: list[RecipeItem] = []
    linea_por_nombre: dict[str, OpcionIngrediente] = {}
    for linea in opcion.ingredientes:
        ing = _to_ingredient(linea.alimento)
        items.append(
            RecipeItem(
                ingredient=ing,
                base_qty=linea.cantidad,
                fixed=linea.fijo,
                min_qty=linea.min_qty,
                max_qty=linea.max_qty,
            )
        )
        linea_por_nombre[ing.name] = linea

    res = adjust_recipe(items, target)
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
