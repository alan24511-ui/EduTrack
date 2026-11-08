-- Migración aditiva para las dos funciones que no tienen tabla en el esquema recibido.
-- Ejecutar una sola vez en el proyecto Supabase antes de habilitar preferencias/plantel.
BEGIN;

CREATE TABLE "Preferencias_Tutor" (
    auth_user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    notificaciones_habilitadas boolean NOT NULL DEFAULT true
);

CREATE TABLE "Configuracion_Plantel" (
    id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    nombre varchar(200) NOT NULL,
    direccion varchar(250) NOT NULL,
    telefono varchar(30) NOT NULL,
    correo varchar(254) NOT NULL
);

ALTER TABLE "Preferencias_Tutor" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Configuracion_Plantel" ENABLE ROW LEVEL SECURITY;

COMMIT;
