"""Dependencias de seguridad para los endpoints protegidos.

El identificador del tutor y del estudiante NUNCA se reciben del frontend:
siempre se resuelven en el servidor a partir del token de Supabase.
"""

from fastapi import Depends, Header, HTTPException

from app.supabase_auth import obtener_usuario


def usuario_actual(authorization: str = Header(default="")) -> dict:
    """Valida el JWT de Supabase y devuelve el usuario autenticado."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Falta el token de acceso.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Falta el token de acceso.")
    return obtener_usuario(token)


def usuario_verificado(usuario: dict = Depends(usuario_actual)) -> dict:
    """Igual que usuario_actual pero exige el correo verificado."""
    if not usuario.get("email_confirmed_at"):
        raise HTTPException(
            status_code=403,
            detail="Debes verificar tu correo electrónico antes de continuar.",
        )
    return usuario
