-- Ejecutar SOLO en una base de datos NUEVA y vacía.
-- No ejecutar sobre la base de datos de producción bditalia.
BEGIN;
CREATE TABLE personal (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 cedula TEXT NOT NULL UNIQUE,
 nombre_completo TEXT NOT NULL,
 contraseña TEXT NOT NULL,
 puesto TEXT NOT NULL,
 perfil INTEGER NOT NULL CHECK (perfil BETWEEN 1 AND 5),
 horario TEXT,
 estado TEXT NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','inactivo')),
 supervisor TEXT,
 fecha_vinculacion DATE,
 fecha_desvinculacion DATE
);
CREATE TABLE personal_datos (
 personal_id BIGINT PRIMARY KEY REFERENCES personal(id) ON DELETE CASCADE,
 nombre_completo_signos TEXT,
 correo_interno TEXT,
 correo_externo TEXT,
 telefono TEXT,
 nota_gis INTEGER CHECK (nota_gis BETWEEN 0 AND 100),
 fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE procesos (
 id INTEGER PRIMARY KEY,
 nombre TEXT NOT NULL UNIQUE
);
CREATE TABLE tipos_evento (
 id INTEGER PRIMARY KEY,
 nombre TEXT NOT NULL UNIQUE
);
CREATE TABLE reportes (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 tipo_reporte TEXT NOT NULL CHECK (tipo_reporte IN ('produccion','evento')),
 timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
 cedula_personal TEXT NOT NULL REFERENCES personal(cedula) ON UPDATE CASCADE,
 cedula_quien_reporta TEXT NOT NULL REFERENCES personal(cedula) ON UPDATE CASCADE,
 supervisor_nombre TEXT,
 fecha_reporte DATE NOT NULL,
 semana INTEGER NOT NULL CHECK (semana BETWEEN 1 AND 53),
 año INTEGER NOT NULL,
 horas NUMERIC(6,2) NOT NULL CHECK (horas >= 0),
 proceso_id INTEGER REFERENCES procesos(id),
 produccion INTEGER CHECK (produccion >= 0),
 aprobados INTEGER CHECK (aprobados >= 0),
 rechazados INTEGER CHECK (rechazados >= 0),
 estado TEXT,
 observaciones TEXT,
 tipo_evento_id INTEGER REFERENCES tipos_evento(id),
 perfil INTEGER,
 puesto TEXT,
 CONSTRAINT reporte_tipo_campos CHECK (
   (tipo_reporte='produccion' AND proceso_id IS NOT NULL AND tipo_evento_id IS NULL)
   OR (tipo_reporte='evento' AND tipo_evento_id IS NOT NULL AND proceso_id IS NULL)
 )
);
CREATE INDEX idx_reportes_fecha_persona ON reportes(fecha_reporte, cedula_personal);
CREATE INDEX idx_reportes_supervisor ON reportes(supervisor_nombre, fecha_reporte);
CREATE TABLE correcciones (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 cedula TEXT NOT NULL REFERENCES personal(cedula) ON UPDATE CASCADE,
 nombre TEXT NOT NULL,
 fecha TIMESTAMPTZ NOT NULL DEFAULT now(),
 id_asociado BIGINT NOT NULL REFERENCES reportes(id) ON DELETE CASCADE,
 tipo_error TEXT,
 solucion TEXT,
 tabla TEXT NOT NULL DEFAULT 'reportes',
 columna TEXT,
 nuevo_valor TEXT,
 estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','corregido'))
);
INSERT INTO procesos(id,nombre) VALUES
 (1,'Producción'),(2,'Control de Calidad'),(3,'Omisiones');
INSERT INTO tipos_evento(id,nombre) VALUES
 (0,'Capacitación'),(1,'Incapacidad'),(2,'Otros'),(3,'Reposición'),
 (4,'Cita CCSS'),(5,'Entregas'),(6,'Fallos'),(7,'Horas Extras'),
 (8,'Fallecimiento'),(9,'Maternidad/Paternidad/Lactancia'),
 (10,'Reunión'),(11,'Supervisión'),(12,'Ubicación'),(13,'Vacaciones'),
 (14,'Horas Ordinarias apoyo Externo'),(15,'Horas Extra apoyo Externo'),
 (16,'Sin Asignación');
COMMIT;
-- IMPORTANTE: crear al menos un usuario administrador (perfil=1) antes de iniciar sesión.
-- Contraseñas heredadas: texto plano, pendiente de migrar a hashes seguros.
