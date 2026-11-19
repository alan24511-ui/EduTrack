
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg import Error as PsycopgError

from app.config import obtener_settings
from app.database import obtener_conexion
from app.routes import auth as rutas_auth
from app.routes import vinculacion as rutas_vinculacion
from app.routes import estudiantes as rutas_estudiantes
from app.routes import tarjetas as rutas_tarjetas
from app.routes import asistencias as rutas_asistencias
from app.routes import dashboard as rutas_dashboard
from app.routes import rfid as rutas_rfid
from app.routes import configuracion as rutas_configuracion
from app.routes import horarios as rutas_horarios
from app.routes import notificaciones as rutas_notificaciones
from app.rfid_reader import configurar_lector


def procesar_uid_serial(uid: str) -> None:
    """Reutiliza la misma lógica de asistencia del endpoint de ingesta RFID."""
    from app.config import obtener_settings
    from app.routes.rfid import procesar_lectura
    from app.schemas import LecturaRFIDEntrada

    settings = obtener_settings()
    if not settings.rfid_device_code:
        raise RuntimeError("Configura ARDUINO_DEVICE_CODE con un dispositivo activo existente.")
    tareas = BackgroundTasks()
    resultado = procesar_lectura(
        LecturaRFIDEntrada(uid=uid, codigo_dispositivo=settings.rfid_device_code),
        tareas,
        settings.rfid_ingest_token,
    )
    if tareas.tasks:
        asyncio.run(tareas())
    logging.getLogger(__name__).info("Resultado lectura RFID %s: %s", uid, resultado.get("resultado"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = obtener_settings()
    lector = configurar_lector(settings.rfid_serial_baud, settings.rfid_serial_port, procesar_uid_serial)
    lector.start()
    yield
    lector.stop()

app = FastAPI(
    title="EduTrack API",
    description="API para el sistema escolar de control de acceso y asistencia.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=obtener_settings().lista_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rutas_auth.router)
app.include_router(rutas_vinculacion.router)
app.include_router(rutas_estudiantes.router)
app.include_router(rutas_tarjetas.router)
app.include_router(rutas_asistencias.router)
app.include_router(rutas_dashboard.router)
app.include_router(rutas_dashboard.router_tutores)
app.include_router(rutas_rfid.router)
app.include_router(rutas_configuracion.router)
app.include_router(rutas_horarios.router)
app.include_router(rutas_notificaciones.router)


@app.get("/health", tags=["Estado"])
def health_check():
    return {
        "status": "ok",
        "message": "EduTrack API funcionando correctamente",
    }

@app.get("/health/db", tags=["Estado"])
def comprobar_base_datos():
    try:
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT 1")
                resultado = cursor.fetchone()

        if resultado != (1,):
            raise HTTPException(
                status_code=503,
                detail="La base de datos no respondió correctamente.",
            )

        return {
            "status": "ok",
            "database": "connected",
            "message": "Conexión con PostgreSQL exitosa",
        }

    except PsycopgError:
        raise HTTPException(
            status_code=503,
            detail="No fue posible conectar con PostgreSQL. Revisa la configuración.",
        )
