"""Motor de ajuste de macros.

Dada una lista de ingredientes (con cantidad de partida) y unos macros objetivo,
recalcula las cantidades para acercarse al objetivo lo máximo posible.

Reglas:
  - Ingredientes por peso (gramos): cantidad continua.
  - Ingredientes por unidad (huevo, plátano): cantidad ENTERA.
  - Ingredientes marcados como fijos: no se tocan.
  - Se reparte el error para que NINGÚN macro quede muy lejos: se minimiza la
    peor desviación (normalizada por su tolerancia). La prioridad
    Kcal > Proteína > Grasa > Hidratos se usa como desempate cuando hay varias
    soluciones igual de buenas.

Modelo: optimización entera-mixta (MILP) resuelta con scipy.optimize.milp, en
dos fases:
  Fase 1 - minimizar z = max_m(desviación_m / tolerancia_m).  (reparte)
  Fase 2 - con z casi fijo, minimizar la suma ponderada de desviaciones según
           prioridad.                                          (desempata)

Módulo puro: no sabe nada de la base de datos.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

MACROS = ("kcal", "protein", "fat", "carbs")

# Peso de cada macro en el desempate (fase 2). Refleja Kcal > Prote > Grasa > HC.
DEFAULT_PRIORITY = {"kcal": 4.0, "protein": 3.0, "fat": 2.0, "carbs": 1.0}


@dataclass
class Ingredient:
    """Valores nutricionales. Por peso: por 100 g. Por unidad: por 1 unidad."""
    name: str
    kcal: float
    protein: float
    carbs: float
    fat: float
    per_unit: bool = False


@dataclass
class RecipeItem:
    ingredient: Ingredient
    base_qty: float
    fixed: bool = False
    min_qty: float = 0.0
    max_qty: float | None = None


@dataclass
class Target:
    kcal: float
    protein: float
    carbs: float
    fat: float


@dataclass
class Result:
    quantities: dict          # nombre_ingrediente -> cantidad ajustada
    totals: dict              # macro -> total conseguido
    target: dict              # macro -> objetivo
    deviations: dict          # macro -> |conseguido - objetivo|
    within_margin: dict       # macro -> bool
    feasible: bool
    message: str = ""


def _qty_coeff(item: RecipeItem, macro: str) -> float:
    """Aporte de 1 unidad de variable a un macro (por 100 g -> /100)."""
    val = getattr(item.ingredient, macro)
    return val if item.ingredient.per_unit else val / 100.0


def adjust_recipe(
    items: list[RecipeItem],
    target: Target,
    kcal_tolerance: float = 20.0,
    gram_tolerance: float = 2.0,
    priority: dict[str, float] | None = None,
    lex_epsilon: float = 1e-3,
) -> Result:
    """Ajusta las cantidades para acercarse a los macros objetivo.

    Devuelve la mejor aproximación posible y marca en `within_margin` qué macros
    quedaron dentro de tolerancia. `feasible=False` solo si el solver falla.
    """
    if not items:
        raise ValueError("La receta no tiene ingredientes.")
    for m in MACROS:
        if getattr(target, m) < 0:
            raise ValueError(f"El objetivo de {m} no puede ser negativo.")

    priority = priority or DEFAULT_PRIORITY
    tol = {m: (kcal_tolerance if m == "kcal" else gram_tolerance) for m in MACROS}
    target_map = {m: float(getattr(target, m)) for m in MACROS}

    adjustable = [it for it in items if not it.fixed]
    fixed_items = [it for it in items if it.fixed]

    n_adj = len(adjustable)
    col_item = {id(it): i for i, it in enumerate(adjustable)}
    col_over = {m: n_adj + 2 * k for k, m in enumerate(MACROS)}
    col_under = {m: n_adj + 2 * k + 1 for k, m in enumerate(MACROS)}
    col_z = n_adj + 2 * len(MACROS)
    n_vars = col_z + 1

    const = {m: sum(_qty_coeff(it, m) * it.base_qty for it in fixed_items)
             for m in MACROS}

    # Balance por macro: sum(coef*x) - over + under == target - const
    balance_rows, balance_rhs = [], []
    for m in MACROS:
        row = np.zeros(n_vars)
        for it in adjustable:
            row[col_item[id(it)]] = _qty_coeff(it, m)
        row[col_over[m]] = -1.0
        row[col_under[m]] = 1.0
        balance_rows.append(row)
        balance_rhs.append(target_map[m] - const[m])
    balance = LinearConstraint(
        np.array(balance_rows), np.array(balance_rhs), np.array(balance_rhs)
    )

    # Minimax: (over_m + under_m) - tol_m * z <= 0  ->  z >= desviación_m / tol_m
    minimax_rows = []
    for m in MACROS:
        row = np.zeros(n_vars)
        row[col_over[m]] = 1.0
        row[col_under[m]] = 1.0
        row[col_z] = -tol[m]
        minimax_rows.append(row)
    minimax = LinearConstraint(
        np.array(minimax_rows), -np.inf, np.zeros(len(MACROS))
    )

    lb = np.zeros(n_vars)
    ub = np.full(n_vars, np.inf)
    integrality = np.zeros(n_vars)
    for it in adjustable:
        j = col_item[id(it)]
        lb[j] = it.min_qty
        ub[j] = np.inf if it.max_qty is None else it.max_qty
        if it.ingredient.per_unit:
            integrality[j] = 1
    bounds = Bounds(lb, ub)

    # Fase 1: minimizar z (la peor desviación normalizada).
    c1 = np.zeros(n_vars)
    c1[col_z] = 1.0
    res = milp(c1, constraints=[balance, minimax], integrality=integrality,
               bounds=bounds, options={"disp": False})
    if not res.success:
        return Result({}, {}, target_map, {}, {}, False,
                      f"El solver falló repartiendo el error: {res.message}")
    z_best = res.x[col_z]

    # Fase 2: con z casi fijo, minimizar la suma ponderada por prioridad.
    z_cap_row = np.zeros(n_vars)
    z_cap_row[col_z] = 1.0
    z_cap = LinearConstraint(z_cap_row, -np.inf, z_best + lex_epsilon)

    c2 = np.zeros(n_vars)
    for m in MACROS:
        w = priority[m] / tol[m]
        c2[col_over[m]] = w
        c2[col_under[m]] = w
    res = milp(c2, constraints=[balance, minimax, z_cap], integrality=integrality,
               bounds=bounds, options={"disp": False})
    if not res.success:
        return Result({}, {}, target_map, {}, {}, False,
                      f"El solver falló en el desempate: {res.message}")

    x = res.x
    quantities: dict[str, float] = {}
    for it in items:
        if it.fixed:
            quantities[it.ingredient.name] = it.base_qty
        else:
            val = x[col_item[id(it)]]
            quantities[it.ingredient.name] = (
                int(round(val)) if it.ingredient.per_unit else round(float(val), 1)
            )

    totals = {m: round(float(const[m]
                       + sum(_qty_coeff(it, m) * quantities[it.ingredient.name]
                             for it in adjustable)), 1)
              for m in MACROS}
    deviations = {m: round(abs(totals[m] - target_map[m]), 1) for m in MACROS}
    within_margin = {m: deviations[m] <= tol[m] for m in MACROS}

    return Result(quantities, totals, target_map, deviations, within_margin, True)
