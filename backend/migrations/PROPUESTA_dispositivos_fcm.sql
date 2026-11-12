-- PROPUESTA solamente. No ejecutar sin aprobación explícita y validar primero el esquema real.
-- Tabla aditiva: un tutor puede tener varios dispositivos; el token es único y actualizable.
CREATE TABLE "Dispositivos_FCM" (
    id bigserial PRIMARY KEY,
    auth_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token text NOT NULL UNIQUE,
    activo boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT dispositivos_fcm_token_no_vacio CHECK (length(trim(token)) >= 20)
);

CREATE INDEX dispositivos_fcm_usuario_activo_idx
    ON "Dispositivos_FCM" (auth_user_id) WHERE activo=TRUE;

ALTER TABLE "Dispositivos_FCM" ENABLE ROW LEVEL SECURITY;
-- No se crea policy para clientes. Solo FastAPI accede usando PostgreSQL privado;
-- el cliente web registra el token por el endpoint con sesión Supabase verificada.
