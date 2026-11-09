"""Preferencias propias del tutor y configuración administrativa del plantel."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.schemas import PlantelActualizar, PreferenciasTutor
from app.security import obtener_rol, usuario_verificado

router = APIRouter(tags=["Configuración"])


def _tutor(usuario: dict) -> None:
    if obtener_rol(usuario["id"]) != "tutor":
        raise HTTPException(status_code=403, detail="Esta operación es exclusiva para tutores.")


def _admin(usuario: dict) -> None:
    if obtener_rol(usuario["id"]) not in {"administrador", "superadministrador"}:
        raise HTTPException(status_code=403, detail="Esta operación requiere permisos de administrador.")


@router.get("/tutores/me/preferencias")
def obtener_preferencias(usuario: dict = Depends(usuario_verificado)):
    _tutor(usuario)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('SELECT notificaciones_habilitadas FROM "Preferencias_Tutor" WHERE auth_user_id=%s', (usuario["id"],))
            fila = cur.fetchone()
        return {"notificacionesHabilitadas": fila[0] if fila else True}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible consultar las preferencias.") from error


@router.put("/tutores/me/preferencias")
def actualizar_preferencias(datos: PreferenciasTutor, usuario: dict = Depends(usuario_verificado)):
    _tutor(usuario)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "Preferencias_Tutor" (auth_user_id, notificaciones_habilitadas) VALUES (%s,%s) '
                'ON CONFLICT (auth_user_id) DO UPDATE SET notificaciones_habilitadas=EXCLUDED.notificaciones_habilitadas '
                'RETURNING notificaciones_habilitadas',
                (usuario["id"], datos.notificaciones_habilitadas),
            )
            enabled = cur.fetchone()[0]
        return {"notificacionesHabilitadas": enabled}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible guardar las preferencias.") from error


@router.get("/configuracion/plantel")
def consultar_plantel(usuario: dict = Depends(usuario_verificado)):
    _admin(usuario)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('SELECT nombre, direccion, telefono, correo FROM "Configuracion_Plantel" WHERE id=1')
            row = cur.fetchone()
        if row is None:
            return {"nombre": "", "direccion": "", "telefono": "", "correo": "", "configurado": False}
        return {"nombre": row[0], "direccion": row[1], "telefono": row[2], "correo": row[3], "configurado": True}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible consultar la configuración institucional.") from error


@router.put("/configuracion/plantel")
def actualizar_plantel(datos: PlantelActualizar, usuario: dict = Depends(usuario_verificado)):
    _admin(usuario)
    if any(not value.strip() for value in (datos.nombre, datos.direccion, datos.telefono)):
        raise HTTPException(status_code=422, detail="Completa todos los datos institucionales.")
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "Configuracion_Plantel" (id,nombre,direccion,telefono,correo) VALUES (1,%s,%s,%s,%s) '
                'ON CONFLICT (id) DO UPDATE SET nombre=EXCLUDED.nombre, direccion=EXCLUDED.direccion, '
                'telefono=EXCLUDED.telefono, correo=EXCLUDED.correo '
                'RETURNING nombre,direccion,telefono,correo',
                (datos.nombre.strip(), datos.direccion.strip(), datos.telefono.strip(), str(datos.correo)),
            )
            row = cur.fetchone()
        return {"nombre": row[0], "direccion": row[1], "telefono": row[2], "correo": row[3], "configurado": True}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible guardar la configuración institucional.") from error
