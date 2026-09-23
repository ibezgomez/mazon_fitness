# Backend Mazón Fitness

Backend del área de nutrición: base de datos multi-tenant (Postgres + RLS),
motor de ajuste de macros y API (FastAPI) con auth por JWT.

## Necesitas
- **Docker Desktop** (para Postgres).
- **Python 3.12+**.

## Puesta en marcha

```bash
# 1. Entra en la carpeta
cd nutricion_backend

# 2. Entorno virtual + dependencias
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 3. Variables de entorno
copy .env.example .env            # macOS/Linux: cp .env.example .env
#   -> abre .env y pon un SECRET_KEY largo y aleatorio

# 4. Levanta Postgres (Docker)
docker compose up -d

# 5. (solo la 1a vez, si el rol 'app' no se creo por el montaje en Windows)
docker compose exec db psql -U postgres -d nutricion -c "ALTER ROLE app WITH LOGIN PASSWORD 'app';"

# 6. Crea/actualiza las tablas y politicas
python -m alembic upgrade head

# 7. Arranca la API
uvicorn app.main:app --reload
```

Abre **http://127.0.0.1:8000/docs** - ahi tienes toda la API para probar.

## Probar la API desde /docs
1. `POST /auth/signup` -> crea un entrenador (nombre, email, contrasena).
2. Boton **Authorize** (arriba a la derecha) -> mete el email y la contrasena ->
   te loguea y guarda el token.
3. Ya puedes usar `POST/GET/PUT/DELETE /alimentos`.

## Tests
```bash
python -m scripts.test_api    # API (auth + CRUD) sobre SQLite, sin Docker
python -m scripts.test_planes # flujo receta->comida->ajuste (SQLite, sin Docker)
python -m scripts.test_clientes # CRUD de clientes (SQLite, sin Docker)
python -m scripts.test_rls    # aislamiento multi-tenant, requiere Postgres arrancado
```

## Notas
- Nos conectamos con el rol `app` (no superusuario) porque Postgres **se salta el
  RLS** con superusuarios. El aislamiento entre entrenadores depende de eso.
- Postgres corre en el puerto **5433** (para no chocar con un Postgres local que
  suele ocupar el 5432).
- Empezar de cero del todo (borra datos): `docker compose down -v && docker compose up -d`.
