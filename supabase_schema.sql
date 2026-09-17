-- ==============================================================================
-- KNS - SISTEMA DE GESTIÓN EN KINESIOLOGÍA
-- Script SQL DDL para Base de Datos y Almacenamiento
-- ==============================================================================

-- 1. Habilitar extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 2. TABLA: USUARIOS DEL SISTEMA (AUTENTICACIÓN Y ROLES)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL DEFAULT 'kinesio' CHECK (rol IN ('admin', 'kinesio')),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Usuarios iniciales:
-- 1. fcendra (admin) -> clave: C4n1ch3r1426
-- 2. anita (kinesio) -> clave: bella2026
INSERT INTO public.usuarios (id, username, password_hash, nombre, rol, activo)
VALUES
    ('u1111111-1111-1111-1111-111111111111', 'fcendra', '4e58b8849b2520dafdc14df8b5b5465e94b29dc99c36df86d5e7ca6094b819f7', 'Federico Cendra', 'admin', true),
    ('u2222222-2222-2222-2222-222222222222', 'anita', 'e551fb264cfc24cb34f2d70cb65fbf8032c52aa5bcfe6e0f498c47462fa112d7', 'Anita', 'kinesio', true)
ON CONFLICT (username) DO UPDATE 
SET password_hash = EXCLUDED.password_hash, rol = EXCLUDED.rol, activo = true;

-- ==============================================================================
-- 3. TABLA: CONFIGURACIÓN GENERAL Y LOGO
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.configuracion (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'app_config',
    clinic_name VARCHAR(255) DEFAULT 'KNS',
    subtitle VARCHAR(255) DEFAULT 'KINESIOLOGÍA',
    logo_icon VARCHAR(50) DEFAULT '🩺',
    custom_logo_url TEXT,
    phone VARCHAR(50) DEFAULT '+5491112345678',
    address VARCHAR(255) DEFAULT 'Consultorio Central',
    work_start_hour INTEGER DEFAULT 8,
    work_end_hour INTEGER DEFAULT 15,
    max_simultaneous_patients INTEGER DEFAULT 2,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO public.configuracion (id, clinic_name, subtitle, logo_icon)
VALUES ('app_config', 'KNS', 'KINESIOLOGÍA', '🩺')
ON CONFLICT (id) DO NOTHING;

-- ==============================================================================
-- 4. TABLA: PACIENTES
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.pacientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre_completo VARCHAR(255) NOT NULL,
    dni VARCHAR(30),
    fecha_nacimiento DATE,
    edad INTEGER CHECK (edad >= 0 AND edad <= 125),
    telefono VARCHAR(50),
    obra_social VARCHAR(100) DEFAULT 'Particular',
    numero_afiliado VARCHAR(100),
    monto_coseguro_default NUMERIC(10,2) DEFAULT 0,
    patologia TEXT,
    sesiones_totales INTEGER NOT NULL DEFAULT 10 CHECK (sesiones_totales >= 0),
    sesiones_realizadas INTEGER NOT NULL DEFAULT 0 CHECK (sesiones_realizadas >= 0),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    notas_generales TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Migraciones seguras si la tabla ya existía
ALTER TABLE public.pacientes ADD COLUMN IF NOT EXISTS fecha_nacimiento DATE;
ALTER TABLE public.pacientes ADD COLUMN IF NOT EXISTS numero_afiliado VARCHAR(100);
ALTER TABLE public.pacientes ADD COLUMN IF NOT EXISTS monto_coseguro_default NUMERIC(10,2) DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_pacientes_nombre ON public.pacientes (nombre_completo);
CREATE INDEX IF NOT EXISTS idx_pacientes_dni ON public.pacientes (dni);
CREATE INDEX IF NOT EXISTS idx_pacientes_activo ON public.pacientes (activo);

-- ==============================================================================
-- 5. TABLA: TURNOS (AGENDA DE 08:00 A 15:00 HS)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.turnos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id UUID NOT NULL REFERENCES public.pacientes(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    duracion_minutos INTEGER NOT NULL DEFAULT 45 CHECK (duracion_minutos IN (30, 45, 60)),
    estado VARCHAR(30) NOT NULL DEFAULT 'Pendiente' CHECK (estado IN ('Pendiente', 'Asistió', 'Cancelado', 'Reprogramado', 'Ausente')),
    monto_coseguro NUMERIC(10,2) DEFAULT 0,
    estado_pago VARCHAR(30) NOT NULL DEFAULT 'Pendiente' CHECK (estado_pago IN ('Pendiente', 'Abonado', 'Parcial', 'Exento')),
    motivo_ajuste TEXT,
    notas TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Migraciones seguras para turnos
ALTER TABLE public.turnos ADD COLUMN IF NOT EXISTS monto_coseguro NUMERIC(10,2) DEFAULT 0;
ALTER TABLE public.turnos ADD COLUMN IF NOT EXISTS estado_pago VARCHAR(30) DEFAULT 'Pendiente';

CREATE INDEX IF NOT EXISTS idx_turnos_fecha ON public.turnos (fecha);
CREATE INDEX IF NOT EXISTS idx_turnos_paciente ON public.turnos (paciente_id);
CREATE INDEX IF NOT EXISTS idx_turnos_estado ON public.turnos (estado);

-- ==============================================================================
-- 6. TABLA: PAGOS Y COSEGUROS (GESTIÓN DE COBROS Y SALDOS)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.pagos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id UUID NOT NULL REFERENCES public.pacientes(id) ON DELETE CASCADE,
    turno_id UUID REFERENCES public.turnos(id) ON DELETE SET NULL,
    fecha_pago DATE NOT NULL DEFAULT CURRENT_DATE,
    monto NUMERIC(10,2) NOT NULL CHECK (monto >= 0),
    monto_total_esperado NUMERIC(10,2), -- Total pactado en caso de pagos parciales / señas
    concepto VARCHAR(150) NOT NULL, -- "Coseguro Sesión", "Sesión Particular", "Tratamiento Completo", "Seña / Pago Parcial", etc.
    modalidad VARCHAR(50) NOT NULL DEFAULT 'Por sesión' CHECK (modalidad IN ('Por sesión', 'Tratamiento completo', 'Pago parcial / Seña')),
    metodo_pago VARCHAR(50) NOT NULL DEFAULT 'Efectivo' CHECK (metodo_pago IN ('Efectivo', 'Transferencia / MP', 'Tarjeta Débito', 'Tarjeta Crédito', 'Otro')),
    sesiones_cubiertas INTEGER DEFAULT 1,
    notas TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pagos_paciente ON public.pagos (paciente_id);
CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON public.pagos (fecha_pago);
CREATE INDEX IF NOT EXISTS idx_pagos_turno ON public.pagos (turno_id);

-- ==============================================================================
-- 7. TABLA: EVOLUCIONES CLÍNICAS (HISTORIAL MÉDICO)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.evoluciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id UUID NOT NULL REFERENCES public.pacientes(id) ON DELETE CASCADE,
    turno_id UUID REFERENCES public.turnos(id) ON DELETE SET NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    nota_clinica TEXT NOT NULL,
    tratamiento_aplicado TEXT,
    escala_dolor_eva INTEGER CHECK (escala_dolor_eva BETWEEN 0 AND 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evoluciones_paciente ON public.evoluciones (paciente_id);
CREATE INDEX IF NOT EXISTS idx_evoluciones_fecha ON public.evoluciones (fecha);

-- ==============================================================================
-- 8. TABLA: ARCHIVOS ADJUNTOS (ÓRDENES, RADIOGRAFÍAS, RESONANCIAS)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.archivos_pacientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id UUID NOT NULL REFERENCES public.pacientes(id) ON DELETE CASCADE,
    nombre_archivo VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    tipo_documento VARCHAR(100) DEFAULT 'Orden Médica',
    tamano_bytes BIGINT,
    public_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_archivos_paciente ON public.archivos_pacientes (paciente_id);

-- ==============================================================================
-- 8. FUNCIÓN Y TRIGGER: CONTROL AUTOMÁTICO DE SESIONES POR ASISTENCIA
-- ==============================================================================
CREATE OR REPLACE FUNCTION sync_paciente_sesiones()
RETURNS TRIGGER AS $$
DECLARE
    target_paciente_id UUID;
    total_asistencias INTEGER;
BEGIN
    IF (TG_OP = 'DELETE') THEN
        target_paciente_id := OLD.paciente_id;
    ELSE
        target_paciente_id := NEW.paciente_id;
    END IF;

    -- Contar turnos con estado 'Asistió'
    SELECT COUNT(*) INTO total_asistencias
    FROM public.turnos
    WHERE paciente_id = target_paciente_id AND estado = 'Asistió';

    -- Actualizar contador en la tabla pacientes
    UPDATE public.pacientes
    SET sesiones_realizadas = total_asistencias,
        updated_at = NOW()
    WHERE id = target_paciente_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_sesiones_turnos ON public.turnos;
CREATE TRIGGER trg_sync_sesiones_turnos
AFTER INSERT OR UPDATE OR DELETE ON public.turnos
FOR EACH ROW
EXECUTE FUNCTION sync_paciente_sesiones();

-- ==============================================================================
-- 9. CONFIGURACIÓN DE ALMACENAMIENTO (STORAGE BUCKET)
-- ==============================================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('pacientes-adjuntos', 'pacientes-adjuntos', true)
ON CONFLICT (id) DO UPDATE SET public = true;

DROP POLICY IF EXISTS "Acceso publico lectura adjuntos" ON storage.objects;
CREATE POLICY "Acceso publico lectura adjuntos"
ON storage.objects FOR SELECT
USING (bucket_id = 'pacientes-adjuntos');

DROP POLICY IF EXISTS "Permitir subida de adjuntos" ON storage.objects;
CREATE POLICY "Permitir subida de adjuntos"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'pacientes-adjuntos');

DROP POLICY IF EXISTS "Permitir eliminacion de adjuntos" ON storage.objects;
CREATE POLICY "Permitir eliminacion de adjuntos"
ON storage.objects FOR DELETE
USING (bucket_id = 'pacientes-adjuntos');

-- ==============================================================================
-- 10. POLÍTICAS ROW LEVEL SECURITY (RLS)
-- ==============================================================================
ALTER TABLE public.usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.configuracion ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pacientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.turnos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pagos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evoluciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.archivos_pacientes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir todo en usuarios" ON public.usuarios;
CREATE POLICY "Permitir todo en usuarios" ON public.usuarios FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir todo en configuracion" ON public.configuracion;
CREATE POLICY "Permitir todo en configuracion" ON public.configuracion FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir todo en pacientes" ON public.pacientes;
CREATE POLICY "Permitir todo en pacientes" ON public.pacientes FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir todo en turnos" ON public.turnos;
CREATE POLICY "Permitir todo en turnos" ON public.turnos FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir todo en pagos" ON public.pagos;
CREATE POLICY "Permitir todo en pagos" ON public.pagos FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir todo en evoluciones" ON public.evoluciones;
CREATE POLICY "Permitir todo en evoluciones" ON public.evoluciones FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir todo en archivos_pacientes" ON public.archivos_pacientes;
CREATE POLICY "Permitir todo en archivos_pacientes" ON public.archivos_pacientes FOR ALL USING (true) WITH CHECK (true);

-- ==============================================================================
-- 11. DATOS DE PRUEBA INICIALES (KINESIOLOGÍA)
-- ==============================================================================
INSERT INTO public.pacientes (id, nombre_completo, dni, fecha_nacimiento, edad, telefono, obra_social, numero_afiliado, monto_coseguro_default, patologia, sesiones_totales, sesiones_realizadas, activo, notas_generales)
VALUES
    ('a1111111-1111-1111-1111-111111111111', 'Carlos Menéndez', '28456123', '1980-05-14', 46, '+5491144445555', 'OSDE 210', '0210-482910-01', 3500, 'Lumbalgia mecánica con irradiación a miembro inferior derecho', 10, 3, true, 'Derivado por Dr. Rossi. Trae RMN lumbar.'),
    ('a2222222-2222-2222-2222-222222222222', 'Florencia Varela', '34123890', '1994-08-22', 32, '+5491155556666', 'Swiss Medical', 'SM-9831204', 4000, 'Tendinopatía del manguito rotador derecho', 10, 5, true, 'Dolor en abducción > 90°. Deportista aficionada (crossfit).'),
    ('a3333333-3333-3333-3333-333333333333', 'Esteban Lamponne', '25890432', '1976-11-03', 50, '+5491166667777', 'Particular', NULL, 12000, 'Esguince de tobillo grado II (LPAA)', 8, 1, true, 'Fase subaguda con edema residual. Buena respuesta al vendaje funcional.')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.turnos (id, paciente_id, fecha, hora_inicio, hora_fin, duracion_minutos, estado, monto_coseguro, estado_pago, motivo_ajuste, notas)
VALUES
    ('b1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', CURRENT_DATE, '08:30:00', '09:15:00', 45, 'Pendiente', 3500, 'Pendiente', NULL, 'Magneto + ejercicios de estabilidad lumbo-pélvica'),
    ('b2222222-2222-2222-2222-222222222222', 'a2222222-2222-2222-2222-222222222222', CURRENT_DATE, '09:00:00', '09:45:00', 45, 'Pendiente', 4000, 'Abonado', NULL, 'Ultrasonido + movilidad escapulotorácica'),
    ('b3333333-3333-3333-3333-333333333333', 'a3333333-3333-3333-3333-333333333333', CURRENT_DATE, '10:00:00', '10:30:00', 30, 'Pendiente', 12000, 'Pendiente', NULL, 'Crioterapia + propiocepción en bosu')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.pagos (id, paciente_id, turno_id, fecha_pago, monto, monto_total_esperado, concepto, modalidad, metodo_pago, sesiones_cubiertas, notas)
VALUES
    ('d1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', NULL, CURRENT_DATE - 5, 3500, NULL, 'Coseguro Sesión 1', 'Por sesión', 'Efectivo', 1, 'Coseguro primera sesión'),
    ('d2222222-2222-2222-2222-222222222222', 'a2222222-2222-2222-2222-222222222222', NULL, CURRENT_DATE - 10, 40000, 40000, 'Tratamiento Completo 10 Sesiones', 'Tratamiento completo', 'Transferencia / MP', 10, 'Abonó paquete completo de 10 coseguros juntos'),
    ('d3333333-3333-3333-3333-333333333333', 'a3333333-3333-3333-3333-333333333333', NULL, CURRENT_DATE - 2, 30000, 96000, 'Seña / Pago Parcial Tratamiento Particular', 'Pago parcial / Seña', 'Transferencia / MP', 3, 'Dejó seña inicial de $30.000 de un total de $96.000 por 8 sesiones')
ON CONFLICT (id) DO NOTHING;

