# EduTrack

Sistema escolar de gestión de estudiantes y asistencia. El frontend es Angular standalone con Bootstrap 5.3.3; la API es FastAPI y usa PostgreSQL/Supabase. La integración planeada del lector es Arduino Uno + RC522 por USB serial hacia un servicio Python local y FastAPI. No se usa Raspberry Pi.

## Estado

El backend contiene operaciones de estudiantes, tarjetas, asistencias, historial y dashboard basadas en el esquema compartido. Falta validar las queries contra la instancia real y las expresiones de checks/RLS. La tabla RFID no tiene columna de activación. Consulta [IMPLEMENTACION_PENDIENTE.md](IMPLEMENTACION_PENDIENTE.md) antes de una prueba real.

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

La API queda en `http://localhost:8000`; Swagger en `/docs`. Variables necesarias: `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `CORS_ORIGINS` y un `RFID_INGEST_TOKEN` aleatorio compartido con el servicio local. Auth usa la clave pública anon y no se incluye ninguna clave privada en Angular.

Auth ofrece registro/verificación OTP, login, perfil, logout, refresh token, reenvío OTP y recuperación/restablecimiento de contraseña. Los cambios de contraseña se completan con OTP tipo `recovery`.

## Servicio del lector

El firmware y el cliente serial están en `firmware/arduino_rc522` y `reader_service`. Instala y configura siguiendo [HARDWARE.md](HARDWARE.md). El servicio envía a `POST /rfid/lecturas`, protegido por token. La API registra entrada y salida diaria; falta prueba física e integración con la base real antes de uso productivo.

## Pruebas

```bash
npm test -- --watch=false
npm run build
cd backend && python -m unittest discover -s tests
cd reader_service && python -m unittest
```

Las pruebas del servicio validan el formato serial con líneas de ejemplo; no prueban el Arduino ni el RC522 físicos. La lista detallada de bloqueos está en [IMPLEMENTACION_PENDIENTE.md](IMPLEMENTACION_PENDIENTE.md).
