"""Test del flujo de entrenamiento (SQLite + TestClient).

Ejecutar:  python -m scripts.test_entrenos
"""
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.db import Base
from app import deps
from app.main import app


def build_client() -> TestClient:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TS = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        db = TS()
        try:
            yield db; db.commit()
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    app.dependency_overrides[deps.get_db] = override
    return TestClient(app)


def main() -> None:
    c = build_client()
    ok = True

    def check(cond: bool, msg: str) -> None:
        nonlocal ok
        print(("OK   " if cond else "FALLO ") + msg)
        ok = ok and cond

    c.post("/auth/signup", json={"nombre": "C", "email": "c@t.com", "password": "secreto123"})
    tok = c.post("/auth/login", data={"username": "c@t.com", "password": "secreto123"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    r = c.post("/ejercicios", headers=H, json={"nombre": "Press banca", "grupo_muscular": "Pecho"})
    check(r.status_code == 201, "crear ejercicio")
    ej = r.json()["id"]
    check(len(c.get("/ejercicios", headers=H).json()) == 1, "listar ejercicios")

    r = c.post("/rutinas", headers=H, json={"nombre": "Full body"})
    check(r.status_code == 201, "crear rutina")
    rid = r.json()["id"]

    dia = c.post(f"/rutinas/{rid}/dias", headers=H, json={"etiqueta": "Lunes - Empuje"}).json()["id"]
    r = c.post(f"/rutina-dias/{dia}/ejercicios", headers=H,
               json={"ejercicio_id": ej, "series": 4, "reps": "8-12", "descanso_seg": 120, "rir": "2"})
    check(r.status_code == 201, "añadir ejercicio al día")

    check(c.post(f"/rutina-dias/{dia}/ejercicios", headers=H,
                 json={"ejercicio_id": str(uuid.uuid4()), "series": 3, "reps": "10"}).status_code == 400,
          "ejercicio inexistente -> 400")

    arbol = c.get(f"/rutinas/{rid}", headers=H).json()
    check(len(arbol["dias"]) == 1 and len(arbol["dias"][0]["ejercicios"]) == 1
          and arbol["dias"][0]["ejercicios"][0]["reps"] == "8-12", "árbol de rutina completo")

    print("\n==>", "TODO OK" if ok else "HAY FALLOS")


if __name__ == "__main__":
    main()
