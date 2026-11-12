"""Envío opcional de correo transaccional mediante el SDK oficial de Resend.

No se conecta ni envía mensajes al importar este módulo. Supabase Auth conserva
su propio SMTP configurado desde el panel; estas funciones son para avisos de la app.
"""

from collections.abc import Sequence
from typing import Any

import resend

from app.config import obtener_settings


def enviar_correo(
    destinatarios: str | Sequence[str],
    asunto: str,
    *,
    html: str,
    texto: str | None = None,
) -> Any:
    """Envía un mensaje transaccional y devuelve la respuesta del SDK de Resend."""
    settings = obtener_settings()
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY no está configurada.")
    if not settings.email_from:
        raise RuntimeError("EMAIL_FROM no está configurada.")

    resend.api_key = settings.resend_api_key
    para = [destinatarios] if isinstance(destinatarios, str) else list(destinatarios)
    if not para:
        raise ValueError("Se requiere al menos un destinatario.")

    mensaje: dict[str, Any] = {
        "from": settings.email_from,
        "to": para,
        "subject": asunto,
        "html": html,
    }
    if texto is not None:
        mensaje["text"] = texto
    return resend.Emails.send(mensaje)
