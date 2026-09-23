"""Test del flujo receta -> comida -> opción -> ajuste (SQLite + TestClient).

Cubre: crear receta (con macros calculados), montar dieta/día/comida, añadir la
receta como opción, previsualizar el ajuste (sin guardar), aplicarlo (guarda) y
cambiar la receta de una opción.

Ejecutar:  python -m scripts.test_planes
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

    def alim(nombre, tipo, k, p, cb, g):
        return c.post("/alimentos", headers=H, json={
            "nombre": nombre, "tipo": tipo, "kcal": k, "prote": p, "carbs": cb, "grasa": g
        }).json()["id"]

    pasta = alim("Pasta", "peso", 371, 13, 75, 1.5)
    pollo = alim("Pollo", "peso", 165, 31, 0, 3.6)
    aceite = alim("Aceite", "peso", 884, 0, 0, 100)

    r = c.post("/recetas", headers=H, json={"nombre": "Pasta con pollo", "ingredientes": [
        {"alimento_id": pasta, "cantidad_base": 80},
        {"alimento_id": pollo, "cantidad_base": 100},
        {"alimento_id": aceite, "cantidad_base": 10}]})
    check(r.status_code == 201, "crear receta")
    receta = r.json()
    check(receta["macros"]["kcal"] > 0, "receta trae macros calculados")

    check(c.post("/recetas", headers=H, json={"nombre": "X", "ingredientes": [
        {"alimento_id": str(uuid.uuid4()), "cantidad_base": 10}]}).status_code == 400,
        "receta con alimento inexistente -> 400")

    dieta = c.post("/dietas", headers=H, json={"nombre": "Plan 1"}).json()["id"]
    dia = c.post(f"/dietas/{dieta}/dias", headers=H, json={"etiqueta": "Día 1"}).json()["id"]
    comida = c.post(f"/dias/{dia}/comidas", headers=H, json={
        "nombre": "Comida", "obj_kcal": 600, "obj_prote": 40, "obj_carbs": 70, "obj_grasa": 15
    }).json()["id"]
    check(bool(dieta and dia and comida), "dieta/día/comida creados")

    r = c.post(f"/comidas/{comida}/opciones", headers=H,
               json={"receta_id": receta["id"], "por_defecto": True})
    check(r.status_code == 201 and len(r.json()["ingredientes"]) == 3,
          "añadir opción copia los 3 ingredientes")
    opid = r.json()["id"]

    prev = c.post(f"/opciones/{opid}/previsualizar-ajuste", headers=H).json()
    check(prev["feasible"] and all(prev["within_margin"].values()), "previsualizar dentro de margen")
    com = c.get(f"/comidas/{comida}", headers=H).json()
    cant0 = [i for i in com["opciones"][0]["ingredientes"] if i["alimento_id"] == pasta][0]["cantidad"]
    check(cant0 == 80 and com["opciones"][0]["res_kcal"] is None, "previsualizar NO persiste")

    c.post(f"/opciones/{opid}/aplicar-ajuste", headers=H)
    com = c.get(f"/comidas/{comida}", headers=H).json()
    cant1 = [i for i in com["opciones"][0]["ingredientes"] if i["alimento_id"] == pasta][0]["cantidad"]
    check(cant1 != 80 and com["opciones"][0]["res_kcal"] is not None, "aplicar SÍ persiste")

    otra = c.post("/recetas", headers=H, json={"nombre": "Solo pollo", "ingredientes": [
        {"alimento_id": pollo, "cantidad_base": 150}]}).json()
    r = c.put(f"/opciones/{opid}/receta", headers=H, json={"receta_id": otra["id"]})
    check(r.status_code == 200 and len(r.json()["ingredientes"]) == 1,
          "cambiar receta reemplaza ingredientes")

    print("\n==>", "TODO EL FLUJO OK" if ok else "HAY FALLOS")


if __name__ == "__main__":
    main()
