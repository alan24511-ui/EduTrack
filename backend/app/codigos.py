"""Generación, normalización y hash de códigos de vinculación.

El código en claro solo se muestra una vez (al generarlo). En la base de datos
se guarda únicamente su hash SHA-256.
"""

import hashlib
import secrets

# Alfabeto sin caracteres ambiguos (sin I, O, 0, 1) para facilitar la lectura.
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LONGITUD_CODIGO = 12


def generar_codigo() -> str:
    """Genera un código aleatorio usando el generador criptográfico del sistema."""
    return "".join(secrets.choice(ALFABETO) for _ in range(LONGITUD_CODIGO))


def normalizar_codigo(codigo: str) -> str:
    """Normaliza el código recibido del cliente antes de hashearlo."""
    return codigo.strip().upper().replace("-", "").replace(" ", "")


def hashear_codigo(codigo: str) -> str:
    """Devuelve el hash SHA-256 del código normalizado."""
    return hashlib.sha256(normalizar_codigo(codigo).encode("utf-8")).hexdigest()
