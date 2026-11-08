"""Regla diaria que corresponde a Asistencia UNIQUE(Id_Estudiante, Fecha)."""


def siguiente_evento(hora_entrada, hora_salida) -> str:
    if hora_entrada is None:
        return "entrada"
    if hora_salida is None:
        return "salida"
    return "duplicada"
