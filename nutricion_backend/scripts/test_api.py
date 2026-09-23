"""Test de la API (auth + CRUD de alimentos) sobre SQLite en memoria.

No necesita Postgres ni Docker: monta una BD SQLite temporal y ejerce los
endpoints con el cliente de pruebas de FastAPI. Comprueba la mecánica de la API
(registro, login/JWT, protección por token, validación y CRUD). El aislamiento
multi-tenant (RLS) se valida aparte, contra Postgres, en scripts/test_rls.py.

Ejecutar:  python -m scripts.test_api
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import app.models  # noqa: F401  (registra las tablas)
from app.db import Base
from app import deps
from app.main import app


def build_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # una sola conexión compartida en memoria
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[deps.get_db] = override_get_db
    return TestClient(app)


def main() -> None:
    c = build_client()
    ok = True

    def check(cond: bool, msg: str) -> None:
        nonlocal ok
        print(("OK   " if cond else "FALLO ") + msg)
        ok = ok and cond

    check(c.get("/health").status_code == 200, "health")

    r = c.post("/auth/signup", json={
        "nombre": "Carlos", "email": "carlos@test.com", "password": "secreto123"})
    check(r.status_code == 201, "signup")

    check(c.post("/auth/signup", json={
        "nombre": "X", "email": "carlos@test.com", "password": "secreto123"
    }).status_code == 400, "signup duplicado -> 400")

    r = c.post("/auth/login", data={"username": "carlos@test.com", "password": "secreto123"})
    check(r.status_code == 200, "login")
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    check(c.post("/auth/login", data={"username": "carlos@test.com", "password": "mal"}
                 ).status_code == 401, "login incorrecto -> 401")

    check(c.post("/alimentos", json={"nombre": "Pollo", "kcal": 165, "prote": 31,
          "carbs": 0, "grasa": 3.6}).status_code == 401, "crear sin token -> 401")

    r = c.post("/alimentos", headers=headers, json={
        "nombre": "Pollo", "tipo": "peso", "kcal": 165, "prote": 31, "carbs": 0, "grasa": 3.6})
    check(r.status_code == 201, "crear alimento")
    aid = r.json()["id"]

    check(c.post("/alimentos", headers=headers, json={
        "nombre": "Mal", "kcal": -5, "prote": 1, "carbs": 1, "grasa": 1
    }).status_code == 422, "validación (kcal negativa) -> 422")

    check(len(c.get("/alimentos", headers=headers).json()) == 1, "listar")
    check(c.get(f"/alimentos/{aid}", headers=headers).json()["kcal"] == 165, "obtener")

    r = c.put(f"/alimentos/{aid}", headers=headers, json={"kcal": 170})
    check(r.json()["kcal"] == 170 and r.json()["nombre"] == "Pollo", "editar parcial")

    check(c.delete(f"/alimentos/{aid}", headers=headers).status_code == 204, "borrar")
    check(c.get("/alimentos", headers=headers).json() == [], "vacío tras borrar")

    print("\n==>", "TODOS LOS ENDPOINTS OK" if ok else "HAY FALLOS")


if __name__ == "__main__":
    main()
