"""Dependencias de seguridad para los endpoints protegidos.

El identificador del tutor y del estudiante NUNCA se reciben del frontend:
siempre se resuelven en el servidor a partir del token de Supabase.
"""

from fastapi import Depends, Header, HTTPException
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.supabase_auth import obtener_usuario


def usuario_actual(authorization: str = Header(default="")) -> dict:
    """Valida el JWT de Supabase y devuelve el usuario autenticado."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Falta el token de acceso.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Falta el token de acceso.")
    try:
        usuario = obtener_usuario(token)
    except HTTPException as error:
        if 400 <= error.status_code < 500:
            raise HTTPException(status_code=401, detail="El token de acceso no es válido.") from error
        raise
    if not usuario.get("id"):
        raise HTTPException(status_code=401, detail="El token de acceso no es válido.")
    return usuario


def usuario_verificado(usuario: dict = Depends(usuario_actual)) -> dict:
    """Igual que usuario_actual pero exige el correo verificado."""
    if not usuario.get("email_confirmed_at"):
        raise HTTPException(
            status_code=403,
            detail="Debes verificar tu correo electrónico antes de continuar.",
        )
    return usuario


def es_administrador(auth_user_id: str) -> bool:
    """Consulta el rol en la base usando el id validado por Supabase Auth."""
    try:
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    'SELECT 1 FROM "Administradores" WHERE auth_user_id = %s',
                    (auth_user_id,),
                )
                return cursor.fetchone() is not None
    except PsycopgError as error:
        raise HTTPException(
            status_code=500,
            detail="No fue posible comprobar los permisos de la cuenta.",
        ) from error


def obtener_rol(auth_user_id: str) -> str:
    """Resuelve el rol persistido; nunca confía en claims enviados por el cliente."""
    try:
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute('SELECT "Rol" FROM "Administradores" WHERE auth_user_id = %s', (auth_user_id,))
                fila = cursor.fetchone()
                if fila:
                    rol = str(fila[0]).strip().lower()
                    if rol in {"administrador", "superadministrador"}:
                        return rol
                    raise HTTPException(status_code=403, detail="El rol de administrador no está permitido.")
                cursor.execute('SELECT 1 FROM "Tutores" WHERE auth_user_id = %s', (auth_user_id,))
                if cursor.fetchone():
                    return "tutor"
                raise HTTPException(status_code=403, detail="La cuenta no tiene un rol autorizado.")
    except PsycopgError as error:
        raise HTTPException(status_code=500, detail="No fue posible comprobar los permisos de la cuenta.") from error


def usuario_administrador(usuario: dict = Depends(usuario_verificado)) -> dict:
    """Exige una sesión válida y verificada cuyo usuario figure como admin."""
    if obtener_rol(usuario["id"]) not in {"administrador", "superadministrador"}:
        raise HTTPException(status_code=403, detail="Esta acción requiere permisos de administrador.")
    return usuario
