"""Administración de la tarjeta vigente por estudiante."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.schemas import TarjetaCrear
from app.security import usuario_administrador

router = APIRouter(prefix="/tarjetas", tags=["Tarjetas RFID"])
ZONA = ZoneInfo("America/Mexico_City")


def _traducir(error: PsycopgError):
    if getattr(error, "sqlstate", None) == "23505":
        raise HTTPException(status_code=409, detail="UID duplicado o el estudiante ya tiene una tarjeta.") from error
    if getattr(error, "sqlstate", None) == "23503":
        raise HTTPException(status_code=404, detail="El estudiante no existe.") from error
    raise HTTPException(status_code=500, detail="No fue posible completar la operación.") from error


def _serializar(row):
    desde, hasta = row[5], row[6]
    hoy = datetime.now(ZONA).date()
    activa = (desde is None or desde <= hoy) and (hasta is None or hasta >= hoy)
    return {"idTarjeta": row[0], "uid": row[1], "idEstudiante": row[2], "nombreEstudiante": row[3], "matricula": row[4], "vigenciaInicio": desde, "vigenciaTermino": hasta, "propietario": row[7], "vigente": activa}


@router.get("")
def listar_tarjetas(uid: str | None = Query(default=None, max_length=20), _: dict = Depends(usuario_administrador)):
    sql = ('SELECT c."id_Tarjeta", c."UID_tarjeta", c."Id_Estudiante", e."Nombre", e."Matricula", c."Vigencia_inicio", c."Vigencia_termino", c."Propietario" '
           'FROM "Credenciales_rfid" c JOIN "Estudiantes" e ON e."Id_Estudiante"=c."Id_Estudiante"')
    params: tuple = ()
    if uid:
        sql += ' WHERE upper(c."UID_tarjeta")=upper(%s)'
        params = (uid.strip(),)
    sql += ' ORDER BY e."Nombre"'
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return [_serializar(row) for row in cur.fetchall()]
    except PsycopgError as error:
        _traducir(error)


@router.post("", status_code=201)
def registrar_tarjeta(datos: TarjetaCrear, _: dict = Depends(usuario_administrador)):
    uid = datos.uid.upper()
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('INSERT INTO "Credenciales_rfid" ("UID_tarjeta", "Id_Estudiante", "Propietario", "Vigencia_inicio", "Vigencia_termino") VALUES (%s,%s,%s,%s,%s) RETURNING "id_Tarjeta"', (uid, datos.id_estudiante, datos.propietario, datos.vigencia_inicio, datos.vigencia_termino))
            id_tarjeta = cur.fetchone()[0]
            cur.execute('SELECT c."id_Tarjeta", c."UID_tarjeta", c."Id_Estudiante", e."Nombre", e."Matricula", c."Vigencia_inicio", c."Vigencia_termino", c."Propietario" FROM "Credenciales_rfid" c JOIN "Estudiantes" e ON e."Id_Estudiante"=c."Id_Estudiante" WHERE c."id_Tarjeta"=%s', (id_tarjeta,))
            return _serializar(cur.fetchone())
    except PsycopgError as error:
        _traducir(error)


@router.put("/{id_tarjeta}")
def reemplazar_o_actualizar_tarjeta(id_tarjeta: int, datos: TarjetaCrear, _: dict = Depends(usuario_administrador)):
    """Actualiza UID/estudiante/vigencia, conservando la fila de la tarjeta."""
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('UPDATE "Credenciales_rfid" SET "UID_tarjeta"=%s, "Id_Estudiante"=%s, "Propietario"=%s, "Vigencia_inicio"=%s, "Vigencia_termino"=%s WHERE "id_Tarjeta"=%s', (datos.uid.upper(), datos.id_estudiante, datos.propietario, datos.vigencia_inicio, datos.vigencia_termino, id_tarjeta))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Tarjeta no encontrada.")
            cur.execute('SELECT c."id_Tarjeta", c."UID_tarjeta", c."Id_Estudiante", e."Nombre", e."Matricula", c."Vigencia_inicio", c."Vigencia_termino", c."Propietario" FROM "Credenciales_rfid" c JOIN "Estudiantes" e ON e."Id_Estudiante"=c."Id_Estudiante" WHERE c."id_Tarjeta"=%s', (id_tarjeta,))
            return _serializar(cur.fetchone())
    except PsycopgError as error:
        _traducir(error)
