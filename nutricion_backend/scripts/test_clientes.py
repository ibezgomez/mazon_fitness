"""Test del CRUD de clientes y su relación con dietas (SQLite + TestClient).

Ejecutar:  python -m scripts.test_clientes
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
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
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

    c.post("/auth/signup", json={"nombre": "C", "email": "c@t.com", "password": "secreto123"})
    tok = c.post("/auth/login", data={"username": "c@t.com", "password": "secreto123"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    # crear cliente con objetivo válido
    r = c.post("/clientes", headers=H, json={"nombre": "Juan", "objetivo": "perdida_grasa"})
    check(r.status_code == 201, "crear cliente")
    cid = r.json()["id"]

    # objetivo inválido -> 422
    check(c.post("/clientes", headers=H, json={"nombre": "X", "objetivo": "engordar"}
                 ).status_code == 422, "objetivo inválido -> 422")

    check(len(c.get("/clientes", headers=H).json()) == 1, "listar clientes")
    check(c.get(f"/clientes/{cid}", headers=H).json()["nombre"] == "Juan", "obtener cliente")

    r = c.put(f"/clientes/{cid}", headers=H, json={"objetivo": "volumen"})
    check(r.json()["objetivo"] == "volumen", "editar objetivo")

    # asignar una dieta al cliente
    r = c.post("/dietas", headers=H, json={"nombre": "Plan Juan", "cliente_id": cid})
    check(r.status_code == 201, "crear dieta asignada al cliente")

    # dieta con cliente inexistente -> 400
    check(c.post("/dietas", headers=H, json={"nombre": "X", "cliente_id": str(uuid.uuid4())}
                 ).status_code == 400, "dieta con cliente inexistente -> 400")

    # dietas del cliente
    r = c.get(f"/clientes/{cid}/dietas", headers=H)
    check(r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["nombre"] == "Plan Juan",
          "dietas del cliente")

    # borrar cliente
    check(c.delete(f"/clientes/{cid}", headers=H).status_code == 204, "borrar cliente")
    check(c.get("/clientes", headers=H).json() == [], "sin clientes tras borrar")

    print("\n==>", "TODO OK" if ok else "HAY FALLOS")


if __name__ == "__main__":
    main()
