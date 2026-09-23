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
