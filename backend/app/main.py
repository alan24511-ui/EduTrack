
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from psycopg import Error as PsycopgError

from app.database import obtener_conexion


app = FastAPI(
    title="EduTrack API",
    description="API para el sistema escolar de control de acceso y asistencia.",
    version="1.0.0",
)


# --------------------------------------------------
# 1. Verificar que la API esté funcionando
# --------------------------------------------------

@app.get("/health", tags=["Estado"])
def health_check():
    return {
        "status": "ok",
        "message": "EduTrack API funcionando correctamente",
    }


# --------------------------------------------------
# 2. Verificar la conexión con PostgreSQL
# --------------------------------------------------

@app.get("/health/db", tags=["Estado"])
def verificar_base_datos():
    try:
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return {
            "status": "ok",
            "database": "connected",
            "message": "Conexión con PostgreSQL exitosa",
        }

    except PsycopgError:
        raise HTTPException(
            status_code=503,
            detail="No fue posible conectar con PostgreSQL.",
        )


# --------------------------------------------------
# 3. Modelo de datos que recibirá la API
# --------------------------------------------------

class LecturaTarjeta(BaseModel):
    uid: str


# --------------------------------------------------
# 4. UID conocidos temporalmente para las pruebas
# --------------------------------------------------

TARJETAS_DE_PRUEBA = {
    "A1B2C3D4",
}


# --------------------------------------------------
# 5. Recibir una lectura RFID
# --------------------------------------------------

@app.post("/device/scan", tags=["Dispositivos"])
def escanear_tarjeta(lectura: LecturaTarjeta):
    uid = lectura.uid.strip().upper()

    # Comprobar que el UID tenga un valor válido.
    if not uid or len(uid) > 64:
        raise HTTPException(
            status_code=422,
            detail="El UID no es válido.",
        )

    # Comprobar si el UID está registrado en las pruebas.
    if uid not in TARJETAS_DE_PRUEBA:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "unknown",
                "uid": uid,
                "message": "Tarjeta no registrada",
            },
        )

    # Respuesta cuando la tarjeta es conocida.
    return {
        "status": "recognized",
        "uid": uid,
        "message": "Tarjeta reconocida correctamente",
    }
