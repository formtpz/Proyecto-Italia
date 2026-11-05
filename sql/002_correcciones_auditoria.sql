-- Ejecutar UNA vez en pgAdmin, sobre la BD AWS existente.
-- No modifica los esquemas public ni naturgy.
BEGIN;

-- Retirar dependencia que borraba solicitudes por ON DELETE CASCADE.
ALTER TABLE italia.correcciones
    DROP CONSTRAINT IF EXISTS correcciones_id_asociado_fkey;

-- Mantener el ID histórico incluso si el reporte ya no existe.
-- Ampliar estados para registrar cancelaciones y rechazos.
ALTER TABLE italia.correcciones
    DROP CONSTRAINT IF EXISTS correcciones_estado_check;

ALTER TABLE italia.correcciones
    ADD CONSTRAINT correcciones_estado_check
    CHECK (estado IN ('pendiente', 'corregido', 'rechazada', 'cancelada'));

-- Registrar qué administrador procesó la solicitud.
ALTER TABLE italia.correcciones
    ADD COLUMN IF NOT EXISTS procesado_por VARCHAR(30),
    ADD COLUMN IF NOT EXISTS procesado_en TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS motivo_resolucion TEXT;

-- Historial en italia.correcciones, sin tabla auxiliar.
CREATE INDEX IF NOT EXISTS idx_italia_correcciones_solicitante_estado
    ON italia.correcciones(cedula, estado);
CREATE INDEX IF NOT EXISTS idx_italia_correcciones_fecha
    ON italia.correcciones(fecha);

COMMIT;
