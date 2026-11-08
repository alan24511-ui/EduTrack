# EduTrack

Sistema escolar de gestión de estudiantes y asistencia. El frontend es Angular standalone con Bootstrap 5.3.3; la API es FastAPI y usa PostgreSQL/Supabase. La integración planeada del lector es Arduino Uno + RC522 por USB serial hacia un servicio Python local y FastAPI. No se usa Raspberry Pi.

## Estado

La autenticación de tutores y el flujo de vinculación existen. En este repositorio no están las migraciones ni el esquema SQL de Supabase y el backend no tiene implementados los endpoints de estudiantes, tarjetas, asistencias, historial o dashboard. Las páginas de esos módulos son principalmente presentacionales. Consulta [IMPLEMENTACION_PENDIENTE.md](IMPLEMENTACION_PENDIENTE.md) antes de una prueba real.

## Requisitos

- Node.js compatible con Angular CLI 22 y npm.
- Python 3.11 o posterior (recomendado) y PostgreSQL accesible con el esquema existente.
- Proyecto Supabase con Auth habilitado y correo OTP configurado.
- Para lector físico: Arduino Uno, RC522, conexión USB y adaptación de nivel lógico a 3.3 V.

## Frontend

```bash
npm ci
npm start
```

Abre `http://localhost:4200`. La URL de FastAPI está en `src/environments/environment.ts` (`http://localhost:8000`). Bootstrap 5.3.3 se carga desde CDN en `src/index.html`.

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Completar .env con los valores de la instalación
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000`; Swagger en `/docs`. Variables necesarias: `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` y `CORS_ORIGINS`. No configures `SUPABASE_SERVICE_ROLE_KEY` para las funciones actuales: el cliente Auth usa la clave pública anon; no se incluye ninguna clave en Angular. El backend accede a PostgreSQL con su conexión configurada.

Auth ofrece registro/verificación OTP, login, perfil, logout, refresh token, reenvío OTP y recuperación/restablecimiento de contraseña. Los cambios de contraseña se completan con OTP tipo `recovery`.

## Servicio del lector

El firmware y el cliente serial están en `firmware/arduino_rc522` y `reader_service`. Instala y configura siguiendo [HARDWARE.md](HARDWARE.md). El servicio intenta enviar a `POST /rfid/lecturas`, endpoint que todavía requiere implementación contra el esquema real; por eso no se debe conectar a una operación de asistencia productiva aún.

## Pruebas

```bash
npm test -- --watch=false
npm run build
cd backend && python -m unittest discover -s tests
cd reader_service && python -m unittest
```

Las pruebas del servicio validan el formato serial con líneas de ejemplo; no prueban el Arduino ni el RC522 físicos. La lista detallada de bloqueos está en [IMPLEMENTACION_PENDIENTE.md](IMPLEMENTACION_PENDIENTE.md).
