"""Reglas de entrada y flujo diario de asistencia."""

from datetime import date, datetime, time, timedelta


def clasificar_entrada(llegada: datetime, hora_entrada: time, tolerancia: int) -> str:
    """Devuelve el estado aplicando el límite inclusivo configurado para el horario."""
    limite = datetime.combine(llegada.date(), hora_entrada) + timedelta(minutes=tolerancia)
    return "presente" if llegada.replace(tzinfo=None) <= limite else "retardo"


def siguiente_evento(hora_entrada, hora_salida) -> str:
    if hora_entrada is None:
        return "entrada"
    if hora_salida is None:
        return "salida"
    return "duplicada"
