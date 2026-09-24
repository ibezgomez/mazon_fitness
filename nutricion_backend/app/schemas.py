"""Esquemas Pydantic (validación de entrada y forma de salida de la API)."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth / entrenador -----------------------------------------------------
class TrainerCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class TrainerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Alimentos -------------------------------------------------------------
class AlimentoBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    tipo: Literal["peso", "unidad"] = "peso"
    kcal: float = Field(ge=0)
    prote: float = Field(ge=0)
    carbs: float = Field(ge=0)
    grasa: float = Field(ge=0)
    g_por_unidad: float | None = Field(default=None, ge=0)


class AlimentoCreate(AlimentoBase):
    pass


class AlimentoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=160)
    tipo: Literal["peso", "unidad"] | None = None
    kcal: float | None = Field(default=None, ge=0)
    prote: float | None = Field(default=None, ge=0)
    carbs: float | None = Field(default=None, ge=0)
    grasa: float | None = Field(default=None, ge=0)
    g_por_unidad: float | None = Field(default=None, ge=0)


class AlimentoOut(AlimentoBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


# --- Recetas ---------------------------------------------------------------
class RecetaIngredienteIn(BaseModel):
    alimento_id: uuid.UUID
    cantidad_base: float = Field(gt=0)
    fijo: bool = False
    min_qty: float = Field(default=0.0, ge=0)
    max_qty: float | None = Field(default=None, ge=0)


class RecetaIngredienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    alimento_id: uuid.UUID
    cantidad_base: float
    fijo: bool
    min_qty: float
    max_qty: float | None


class RecetaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    foto_url: str | None = None
    instrucciones: str | None = None
    ingredientes: list[RecetaIngredienteIn] = Field(min_length=1)


class RecetaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=160)
    foto_url: str | None = None
    instrucciones: str | None = None
    # Si se envía, REEMPLAZA por completo la lista de ingredientes.
    ingredientes: list[RecetaIngredienteIn] | None = None


class Macros(BaseModel):
    kcal: float
    prote: float
    carbs: float
    grasa: float


class RecetaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    foto_url: str | None
    instrucciones: str | None
    ingredientes: list[RecetaIngredienteOut]
    macros: Macros


# --- Dietas / días / comidas ----------------------------------------------
class DietaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    cliente_id: uuid.UUID | None = None
    es_plantilla: bool = False


class DietaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    cliente_id: uuid.UUID | None
    es_plantilla: bool


class DiaCreate(BaseModel):
    etiqueta: str = Field(min_length=1, max_length=60)
    orden: int = 0
    obj_kcal: float | None = Field(default=None, ge=0)
    obj_prote: float | None = Field(default=None, ge=0)
    obj_carbs: float | None = Field(default=None, ge=0)
    obj_grasa: float | None = Field(default=None, ge=0)


class DiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    dieta_id: uuid.UUID
    etiqueta: str
    orden: int
    obj_kcal: float | None
    obj_prote: float | None
    obj_carbs: float | None
    obj_grasa: float | None


class ComidaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    orden: int = 0
    obj_kcal: float = Field(ge=0)
    obj_prote: float = Field(ge=0)
    obj_carbs: float = Field(ge=0)
    obj_grasa: float = Field(ge=0)


class OpcionIngredienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    alimento_id: uuid.UUID
    cantidad: float
    fijo: bool
    min_qty: float
    max_qty: float | None


class OpcionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    receta_id: uuid.UUID | None
    orden: int
    por_defecto: bool
    res_kcal: float | None
    res_prote: float | None
    res_carbs: float | None
    res_grasa: float | None
    ingredientes: list[OpcionIngredienteOut]


class ComidaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    dieta_dia_id: uuid.UUID
    nombre: str
    orden: int
    obj_kcal: float
    obj_prote: float
    obj_carbs: float
    obj_grasa: float
    opciones: list[OpcionOut]


# --- Opciones y ajuste -----------------------------------------------------
class OpcionCreate(BaseModel):
    receta_id: uuid.UUID
    por_defecto: bool = False


class CambiarReceta(BaseModel):
    receta_id: uuid.UUID


class AjusteOut(BaseModel):
    """Resultado del motor de macros para una opción de comida."""
    feasible: bool
    quantities: dict[str, float]      # nombre de alimento -> cantidad ajustada
    totals: dict[str, float]          # kcal/protein/carbs/fat conseguidos
    target: dict[str, float]          # objetivos de la comida
    deviations: dict[str, float]      # desviación por macro
    within_margin: dict[str, bool]    # ¿dentro de margen cada macro?


# --- Clientes --------------------------------------------------------------
# Objetivos definidos por el cliente (3 valores).
Objetivo = Literal["perdida_grasa", "volumen", "recomposicion"]


class ClienteCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    objetivo: Objetivo


class ClienteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    objetivo: Objetivo | None = None


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    objetivo: str | None


# --- Dieta completa (árbol) ------------------------------------------------
class DiaConComidas(DiaOut):
    comidas: list[ComidaOut] = []


class DietaDetalle(DietaOut):
    dias: list[DiaConComidas] = []


# ===========================================================================
# ENTRENAMIENTO
# ===========================================================================
class EjercicioBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    grupo_muscular: str | None = Field(default=None, max_length=80)
    video_url: str | None = None
    notas: str | None = None


class EjercicioCreate(EjercicioBase):
    pass


class EjercicioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=160)
    grupo_muscular: str | None = Field(default=None, max_length=80)
    video_url: str | None = None
    notas: str | None = None


class EjercicioOut(EjercicioBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class RutinaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    cliente_id: uuid.UUID | None = None
    es_plantilla: bool = False


class RutinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    cliente_id: uuid.UUID | None
    es_plantilla: bool


class RutinaDiaCreate(BaseModel):
    etiqueta: str = Field(min_length=1, max_length=80)
    orden: int = 0


class RutinaEjercicioCreate(BaseModel):
    ejercicio_id: uuid.UUID
    orden: int = 0
    series: int = Field(default=3, ge=1)
    reps: str = Field(default="", max_length=40)
    descanso_seg: int | None = Field(default=None, ge=0)
    rir: str | None = Field(default=None, max_length=20)
    peso_objetivo: float | None = Field(default=None, ge=0)
    notas: str | None = None


class RutinaEjercicioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ejercicio_id: uuid.UUID
    orden: int
    series: int
    reps: str
    descanso_seg: int | None
    rir: str | None
    peso_objetivo: float | None
    notas: str | None


class RutinaDiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rutina_id: uuid.UUID
    etiqueta: str
    orden: int
    ejercicios: list[RutinaEjercicioOut] = []


class RutinaDetalle(RutinaOut):
    dias: list[RutinaDiaOut] = []
