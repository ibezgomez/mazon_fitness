-- Se ejecuta como superusuario (postgres) al crear la BD por primera vez.
--
-- CLAVE: la app se conecta con el rol 'app', que NO es superusuario. Si se
-- conectara como superusuario, Postgres SALTARÍA las políticas RLS y el
-- aislamiento entre entrenadores no serviría de nada.
--
-- 'app' será dueño del esquema public, así que crea y posee las tablas; con
-- FORCE ROW LEVEL SECURITY (en la migración) el RLS aplica incluso al dueño.

CREATE ROLE app WITH LOGIN PASSWORD 'app';

ALTER SCHEMA public OWNER TO app;
GRANT ALL ON DATABASE nutricion TO app;
