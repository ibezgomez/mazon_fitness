"""App principal de FastAPI — Mazón Fitness."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import alimentos, auth, clientes, planes, recetas

app = FastAPI(title="Mazón Fitness API", version="0.3.0")

# Orígenes del frontend permitidos (Vite usa 5173 por defecto).
origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clientes.router)
app.include_router(alimentos.router)
app.include_router(recetas.router)
app.include_router(planes.router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}