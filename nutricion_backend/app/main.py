"""App principal de FastAPI — Mazón Fitness."""
from __future__ import annotations

from fastapi import FastAPI

from .routers import alimentos, auth

app = FastAPI(title="Mazón Fitness API", version="0.1.0")

app.include_router(auth.router)
app.include_router(alimentos.router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
