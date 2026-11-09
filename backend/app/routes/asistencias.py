"""Historial de asistencia con restricción de alcance para tutores."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.security import obtener_rol, usuario_verificado

router = APIRouter(prefix="/asistencias", tags=["Asistencias"])


@router.get("")
def historial(
    desde: date | None = None,
    hasta: date | None = None,
    q: str = Query(default="", max_length=120),
    grupo: str | None = Query(default=None, max_length=80),
    usuario: dict = Depends(usuario_verificado),
):
    rol = obtener_rol(usuario["id"])
    filtros, params = [], []
    if rol == "tutor":
        filtros.append('EXISTS (SELECT 1 FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" WHERE et."Id_Estudiante"=a."Id_Estudiante" AND et."Autorizado"=TRUE AND t.auth_user_id=%s)')
        params.append(usuario["id"])
    elif rol not in {"administrador", "superadministrador"}:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    if desde:
        filtros.append('a."Fecha">=%s')
        params.append(desde)
    if hasta:
        filtros.append('a."Fecha"<=%s')
        params.append(hasta)
    if desde and hasta and desde > hasta:
        raise HTTPException(status_code=422, detail="La fecha inicial debe ser anterior a la final.")
    if q.strip():
        filtros.append('(e."Nombre" ILIKE %s OR e."Matricula" ILIKE %s)')
        params.extend([f"%{q.strip()}%", f"%{q.strip()}%"])
    if grupo:
        filtros.append('e."Grupo"=%s')
        params.append(grupo.strip())
    where = " WHERE " + " AND ".join(filtros) if filtros else ""
    sql = ('SELECT a."id_asistencia", a."Fecha", a."Hora_Entrada", a."Hora_Salida", a."Asistencia", a."Estado", e."Id_Estudiante", e."Nombre", e."Matricula", e."Grupo" '
           'FROM "Asistencia" a JOIN "Estudiantes" e ON e."Id_Estudiante"=a."Id_Estudiante"' + where + ' ORDER BY a."Fecha" DESC, a."Hora_Entrada" DESC NULLS LAST LIMIT 1000')
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return [{"id": r[0], "fecha": r[1], "horaEntrada": r[2], "horaSalida": r[3], "asistencia": r[4], "estado": r[5], "idEstudiante": r[6], "nombre": r[7], "matricula": r[8], "grupo": r[9]} for r in cur.fetchall()]
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible consultar el historial.") from error
