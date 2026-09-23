"""App principal de FastAPI — Mazón Fitness."""
from __future__ import annotations

from fastapi import FastAPI

from .routers import alimentos, auth, clientes, planes, recetas

app = FastAPI(title="Mazón Fitness API", version="0.2.0")

app.include_router(auth.router)
app.include_router(clientes.router)
app.include_router(alimentos.router)
app.include_router(recetas.router)
app.include_router(planes.router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
