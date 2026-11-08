"""Indicadores consultados de PostgreSQL, sin valores de relleno."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.security import obtener_rol, usuario_verificado

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
router_tutores = APIRouter(prefix="/tutores", tags=["Dashboard de tutores"])
ZONA = ZoneInfo("America/Mexico_City")


@router.get("")
def resumen(usuario: dict = Depends(usuario_verificado)):
    rol = obtener_rol(usuario["id"])
    hoy = datetime.now(ZONA).date()
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            if rol == "tutor":
                cur.execute('SELECT e."Id_Estudiante", e."Nombre", e."Matricula", e."Grupo" FROM "Estudiantes" e WHERE EXISTS (SELECT 1 FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" WHERE et."Id_Estudiante"=e."Id_Estudiante" AND t.auth_user_id=%s AND et."Autorizado"=TRUE) ORDER BY e."Nombre"', (usuario["id"],))
                estudiantes = cur.fetchall()
                ids = [r[0] for r in estudiantes]
                recientes = []
                if ids:
                    cur.execute('SELECT a."Fecha", a."Hora_Entrada", a."Hora_Salida", a."Estado", e."Nombre", e."Matricula", e."Grupo" FROM "Asistencia" a JOIN "Estudiantes" e ON e."Id_Estudiante"=a."Id_Estudiante" WHERE a."Id_Estudiante"=ANY(%s) ORDER BY a."Fecha" DESC LIMIT 20', (ids,))
                    recientes = cur.fetchall()
                return {"rol": rol, "estudiantes": [{"id": r[0], "nombre": r[1], "matricula": r[2], "grupo": r[3]} for r in estudiantes], "ultimasAsistencias": [{"fecha": r[0], "horaEntrada": r[1], "horaSalida": r[2], "estado": r[3], "nombre": r[4], "matricula": r[5], "grupo": r[6]} for r in recientes]}

            if rol not in {"administrador", "superadministrador"}:
                raise HTTPException(status_code=403, detail="Acceso denegado.")
            cur.execute('SELECT count(*) FROM "Estudiantes"')
            total_estudiantes = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM "Credenciales_rfid" WHERE ("Vigencia_inicio" IS NULL OR "Vigencia_inicio"<=%s) AND ("Vigencia_termino" IS NULL OR "Vigencia_termino">=%s)', (hoy, hoy))
            tarjetas_vigentes = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM "Asistencia" WHERE "Fecha"=%s', (hoy,))
            asistencias_dia = cur.fetchone()[0]
            cur.execute('SELECT a."Fecha", a."Hora_Entrada", a."Hora_Salida", a."Estado", e."Nombre", e."Matricula", e."Grupo" FROM "Asistencia" a JOIN "Estudiantes" e ON e."Id_Estudiante"=a."Id_Estudiante" ORDER BY a."Fecha" DESC, a."Hora_Entrada" DESC NULLS LAST LIMIT 10')
            recientes = cur.fetchall()
            cur.execute('SELECT "Nombre", "Estado", "Ultimo_Contacto" FROM "Dispositivos" ORDER BY "Ultimo_Contacto" DESC NULLS LAST')
            dispositivos = cur.fetchall()
            return {"rol": rol, "totalEstudiantes": total_estudiantes, "tarjetasVigentes": tarjetas_vigentes, "asistenciasHoy": asistencias_dia, "inasistencias": None, "ultimosRegistros": [{"fecha": r[0], "horaEntrada": r[1], "horaSalida": r[2], "estado": r[3], "nombre": r[4], "matricula": r[5], "grupo": r[6]} for r in recientes], "lectores": [{"nombre": r[0], "estado": r[1], "ultimoContacto": r[2], "conectado": bool(r[2] and (datetime.now(ZONA) - r[2].astimezone(ZONA)).total_seconds() < 120)} for r in dispositivos]}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible consultar el dashboard.") from error


@router_tutores.get("/dashboard")
def dashboard_tutor(usuario: dict = Depends(usuario_verificado)):
    if obtener_rol(usuario["id"]) != "tutor":
        raise HTTPException(status_code=403, detail="Este dashboard es exclusivo para tutores.")
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT e."Id_Estudiante",e."Nombre",e."Matricula",e."Grupo" '
                'FROM "Estudiantes" e WHERE EXISTS ('
                'SELECT 1 FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" '
                'WHERE et."Id_Estudiante"=e."Id_Estudiante" AND et."Autorizado"=TRUE AND t.auth_user_id=%s) '
                'ORDER BY e."Nombre"', (usuario["id"],),
            )
            estudiantes = cur.fetchall()
            ids = [row[0] for row in estudiantes]
            asistencias = []
            if ids:
                cur.execute(
                    'SELECT a."Fecha",a."Hora_Entrada",a."Hora_Salida",a."Estado",'
                    'e."Id_Estudiante",e."Nombre",e."Matricula",e."Grupo" '
                    'FROM "Asistencia" a JOIN "Estudiantes" e ON e."Id_Estudiante"=a."Id_Estudiante" '
                    'WHERE a."Id_Estudiante"=ANY(%s) AND EXISTS ('
                    'SELECT 1 FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" '
                    'WHERE et."Id_Estudiante"=e."Id_Estudiante" AND et."Autorizado"=TRUE AND t.auth_user_id=%s) '
                    'ORDER BY a."Fecha" DESC LIMIT 50', (ids, usuario["id"]),
                )
                asistencias = cur.fetchall()
        return {
            "estudiantes": [{"id": r[0], "nombre": r[1], "matricula": r[2], "grupo": r[3]} for r in estudiantes],
            "asistencias": [{"fecha": r[0], "horaEntrada": r[1], "horaSalida": r[2], "estado": r[3],
                             "idEstudiante": r[4], "nombre": r[5], "matricula": r[6], "grupo": r[7]} for r in asistencias],
        }
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible consultar el dashboard de tutor.") from error
