"""Prueba de aislamiento multi-tenant (RLS).

Crea dos entrenadores, mete un alimento para cada uno y comprueba que:
  1. Con el tenant A activo solo se ven los datos de A (y con B, los de B).
  2. Sin tenant fijado no se ve NADA.
  3. No se puede insertar una fila con el tenant de otro (WITH CHECK).

IMPORTANTE: debe ejecutarse conectando como el rol 'app' (no superusuario),
tal y como está en DATABASE_URL. Con un superusuario Postgres se salta el RLS y
la prueba no valdría.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.db import SessionLocal, set_tenant
from app.models import Alimento, Trainer


def crear_entrenadores() -> tuple[uuid.UUID, uuid.UUID]:
    with SessionLocal() as s, s.begin():
        a = Trainer(nombre="Entrenador A", email=f"a-{uuid.uuid4()}@x.com")
        b = Trainer(nombre="Entrenador B", email=f"b-{uuid.uuid4()}@x.com")
        s.add_all([a, b])
        s.flush()
        return a.id, b.id


def crear_alimento(tenant_id: uuid.UUID, nombre: str) -> None:
    with SessionLocal() as s, s.begin():
        set_tenant(s, tenant_id)
        s.add(Alimento(tenant_id=tenant_id, nombre=nombre, tipo="peso",
                       kcal=100, prote=1, carbs=1, grasa=1))


def alimentos_visibles(tenant_id: uuid.UUID) -> list[str]:
    with SessionLocal() as s, s.begin():
        set_tenant(s, tenant_id)
        return list(s.execute(select(Alimento.nombre)).scalars().all())


def main() -> None:
    a_id, b_id = crear_entrenadores()
    crear_alimento(a_id, "Alimento de A")
    crear_alimento(b_id, "Alimento de B")

    ok = True

    vis_a = alimentos_visibles(a_id)
    print("1) A ve:", vis_a)
    if vis_a != ["Alimento de A"]:
        ok = False
        print("   FALLO: A debería ver solo lo suyo")

    vis_b = alimentos_visibles(b_id)
    print("   B ve:", vis_b)
    if vis_b != ["Alimento de B"]:
        ok = False
        print("   FALLO: B debería ver solo lo suyo")

    # Sin tenant fijado -> no se ve nada.
    with SessionLocal() as s, s.begin():
        sin = list(s.execute(select(Alimento.nombre)).scalars().all())
    print("2) Sin tenant se ve:", sin)
    if sin != []:
        ok = False
        print("   FALLO: sin tenant no debería verse nada")

    # Insertar con el tenant de otro -> debe fallar (WITH CHECK).
    bloqueado = False
    try:
        with SessionLocal() as s, s.begin():
            set_tenant(s, a_id)                      # tenant A activo...
            s.add(Alimento(tenant_id=b_id, nombre="Colado", tipo="peso",
                           kcal=1, prote=1, carbs=1, grasa=1))  # ...fila de B
    except DBAPIError:
        bloqueado = True
    print("3) ¿Bloquea insertar con tenant ajeno?:", bloqueado)
    if not bloqueado:
        ok = False
        print("   FALLO: debería haber bloqueado el insert")

    print("\n==>", "TODO OK: el aislamiento funciona" if ok else "HAY FALLOS")


if __name__ == "__main__":
    main()
