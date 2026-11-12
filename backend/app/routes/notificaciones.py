"""Registro seguro de tokens FCM del usuario Supabase autenticado."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.security import obtener_rol, usuario_verificado

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


class RegistroDispositivo(BaseModel):
    token: str = Field(min_length=20, max_length=4096)


@router.put("/dispositivo", summary="Registrar o actualizar este dispositivo FCM")
def registrar_dispositivo(datos: RegistroDispositivo, usuario: dict = Depends(usuario_verificado)):
    auth_user_id = usuario["id"]
    if obtener_rol(auth_user_id) != "tutor":
        raise HTTPException(status_code=403, detail="El registro de notificaciones es exclusivo para tutores.")
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "Dispositivos_FCM" (auth_user_id, token, activo, created_at, updated_at) '
                'VALUES (%s, %s, TRUE, now(), now()) '
                'ON CONFLICT (token) DO UPDATE SET activo=TRUE, updated_at=now() '
                'WHERE "Dispositivos_FCM".auth_user_id=EXCLUDED.auth_user_id RETURNING id',
                (auth_user_id, datos.token.strip()),
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=409, detail="Este dispositivo ya está asociado con otra cuenta.")
        return {"registrado": True}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No está disponible el registro FCM. Verifica la tabla propuesta de dispositivos.") from error


@router.delete("/dispositivo", summary="Desactivar el dispositivo FCM actual")
def eliminar_dispositivo(datos: RegistroDispositivo, usuario: dict = Depends(usuario_verificado)):
    if obtener_rol(usuario["id"]) != "tutor":
        raise HTTPException(status_code=403, detail="La baja de notificaciones es exclusiva para tutores.")
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(
                'UPDATE "Dispositivos_FCM" SET activo=FALSE, updated_at=now() '
                'WHERE auth_user_id=%s AND token=%s',
                (usuario["id"], datos.token.strip()),
            )
        return {"registrado": False}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No está disponible el registro FCM.") from error
