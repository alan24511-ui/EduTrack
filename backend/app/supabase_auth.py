"""Cliente HTTP mínimo para Supabase Auth (GoTrue).

EduTrack delega el registro, la verificación OTP y las sesiones en Supabase Auth.
FastAPI actúa como intermediario para que ninguna clave sensible (service_role)
llegue nunca al navegador.
"""

import httpx
from fastapi import HTTPException

from app.config import obtener_settings

TIEMPO_ESPERA = 15


def _url_base() -> str:
    settings = obtener_settings()
    if not settings.supabase_url:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_URL no está configurada en backend/.env.",
        )
    return settings.supabase_url.rstrip("/") + "/auth/v1"


def _clave_api() -> str:
    settings = obtener_settings()
    clave = settings.supabase_anon_key or settings.supabase_service_role_key
    if not clave:
        raise HTTPException(
            status_code=500,
            detail="Falta SUPABASE_ANON_KEY en backend/.env.",
        )
    return clave


def _encabezados(access_token: str | None = None) -> dict[str, str]:
    encabezados = {
        "apikey": _clave_api(),
        "Content-Type": "application/json",
    }
    if access_token:
        encabezados["Authorization"] = f"Bearer {access_token}"
    return encabezados


def _procesar(respuesta: httpx.Response) -> dict:
    """Convierte una respuesta de GoTrue en JSON o en un HTTPException."""
    if respuesta.status_code >= 400:
        try:
            detalle = respuesta.json()
        except ValueError:
            detalle = respuesta.text
        raise HTTPException(status_code=respuesta.status_code, detail=detalle)
    if not respuesta.content:
        return {}
    return respuesta.json()


def registrar_usuario(correo: str, password: str, nombre: str) -> dict:
    """Crea la cuenta en Supabase Auth. Supabase envía el correo de verificación."""
    with httpx.Client(timeout=TIEMPO_ESPERA) as cliente:
        respuesta = cliente.post(
            f"{_url_base()}/signup",
            headers=_encabezados(),
            json={"email": correo, "password": password, "data": {"nombre": nombre}},
        )
    return _procesar(respuesta)


def verificar_otp(correo: str, token: str) -> dict:
    """Verifica el código OTP enviado al correo durante el registro."""
    with httpx.Client(timeout=TIEMPO_ESPERA) as cliente:
        respuesta = cliente.post(
            f"{_url_base()}/verify",
            headers=_encabezados(),
            json={"type": "signup", "email": correo, "token": token},
        )
    return _procesar(respuesta)


def iniciar_sesion(correo: str, password: str) -> dict:
    """Autentica al usuario con correo y contraseña."""
    with httpx.Client(timeout=TIEMPO_ESPERA) as cliente:
        respuesta = cliente.post(
            f"{_url_base()}/token",
            params={"grant_type": "password"},
            headers=_encabezados(),
            json={"email": correo, "password": password},
        )
    return _procesar(respuesta)


def cerrar_sesion(access_token: str) -> None:
    """Invalida la sesión en Supabase Auth."""
    with httpx.Client(timeout=TIEMPO_ESPERA) as cliente:
        respuesta = cliente.post(
            f"{_url_base()}/logout",
            headers=_encabezados(access_token),
        )
    if respuesta.status_code >= 400 and respuesta.status_code != 401:
        _procesar(respuesta)


def obtener_usuario(access_token: str) -> dict:
    """Valida el JWT contra Supabase Auth y devuelve el usuario.

    GoTrue comprueba la firma y la vigencia del token; por eso este endpoint
    es la fuente de verdad para autenticar las peticiones protegidas.
    """
    with httpx.Client(timeout=TIEMPO_ESPERA) as cliente:
        respuesta = cliente.get(
            f"{_url_base()}/user",
            headers=_encabezados(access_token),
        )
    return _procesar(respuesta)
