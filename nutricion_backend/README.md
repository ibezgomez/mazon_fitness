# Backend de nutrición — puesta en marcha desde cero

Objetivo de este hito: levantar la base de datos, crear las tablas y **comprobar
que el aislamiento entre entrenadores (multi-tenant) funciona** antes de montar
nada encima.

## Necesitas instalado
- **Docker Desktop** (para la base de datos, sin ensuciar tu máquina).
- **Python 3.12+**.

## Pasos

```bash
# 1. Entra en la carpeta del proyecto
cd nutricion_backend

# 2. Crea un entorno virtual e instala dependencias
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Crea tu archivo de entorno a partir del ejemplo
cp .env.example .env

# 4. Levanta Postgres (crea también el rol 'app' no superusuario)
docker compose up -d

# 5. Espera a que la BD esté lista (~5 s). Puedes comprobarlo con:
docker compose logs db | grep "database system is ready to accept connections"

# 6. Crea las tablas y activa el RLS
alembic upgrade head

# 7. Ejecuta la prueba de aislamiento multi-tenant
python -m scripts.test_rls
```

## Qué deberías ver en el paso 7

```
1) A ve: ['Alimento de A']
   B ve: ['Alimento de B']
2) Sin tenant se ve: []
3) ¿Bloquea insertar con tenant ajeno?: True

==> TODO OK: el aislamiento funciona
```

Si sale eso, el multi-tenant está validado y podemos construir endpoints encima.

## Por qué el rol 'app' NO es superusuario
Postgres **salta el RLS para los superusuarios**. Si te conectaras como el rol
`postgres`, el test pasaría "viéndolo todo" y no probaría nada. Por eso la app
usa el rol `app` (creado en `scripts/init_roles.sql`), que sí está sujeto a las
políticas.

## Comandos útiles
```bash
# Ver las tablas y políticas por dentro (como superusuario):
docker compose exec db psql -U postgres -d nutricion -c "\dp alimento"

# Empezar de cero del todo (borra los datos y re-ejecuta init_roles.sql):
docker compose down -v && docker compose up -d
```
