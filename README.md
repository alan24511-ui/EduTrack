# EduTrack

Sistema escolar de gestión de estudiantes y asistencia. El frontend es Angular standalone con Bootstrap; la API es FastAPI y usa PostgreSQL/Supabase. FastAPI administra el Arduino UNO + RC522 conectado por USB serial y permite asociar credenciales desde Alumnos.

## Estado

El backend contiene operaciones de estudiantes, tarjetas, asistencias, historial y dashboard sobre el esquema compartido. La integración Arduino/RC522 requiere validación con hardware físico y backend configurado antes de uso productivo. Consulta [IMPLEMENTACION_PENDIENTE.md](IMPLEMENTACION_PENDIENTE.md).

## Requisitos

- Node.js y npm compatibles con Angular del proyecto.
- Python 3.11 o posterior para backend; PostgreSQL accesible y proyecto Supabase con Auth habilitado.
- Lector: Arduino UNO/Nano, RC522, cables SPI y USB; el RC522 se alimenta a 3.3 V.

## Frontend

```bash
npm ci
npm start
```

Abre `http://localhost:4200`. La URL de FastAPI está en `src/environments/environment.ts`.

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Completar .env con valores de la instalación
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

La API queda en `http://localhost:8000`; Swagger en `/docs`. Configura `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `CORS_ORIGINS` y `RFID_INGEST_TOKEN` en el entorno/backend. No publiques secretos.

## Lector Arduino + RC522

Carga el firmware Arduino y conecta el UNO por USB a la computadora donde se ejecuta FastAPI. La API inicia su lector serial automáticamente; no inicies `reader_service/reader_service.py` ni dejes abierto Serial Monitor porque ocuparían el puerto. Consulta [HARDWARE.md](HARDWARE.md) para cableado, arranque y prueba física.

## Servicios cloud y despliegue

La preparación de Supabase, Render, Vercel, Resend y Firebase Cloud Messaging está documentada en [DEPLOYMENT.md](DEPLOYMENT.md). `backend/.env.example` contiene las variables del backend y la URL pública de compilación del frontend; nunca copies secretos a Angular.
