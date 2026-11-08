"""Consulta de horarios publicados y operaciones administrativas."""

from datetime import time

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.schemas import HorarioActualizar, HorarioCrear
from app.security import obtener_rol, usuario_verificado

router = APIRouter(prefix="/horarios", tags=["Horarios"])


def _admin(usuario: dict) -> None:
    if obtener_rol(usuario["id"]) not in {"administrador", "superadministrador"}:
        raise HTTPException(status_code=403, detail="Esta operación requiere permisos de administrador.")


def _salida(row):
    return {"id": row[0], "diaSemana": row[1], "grupo": row[2], "horaEntrada": row[3].strftime("%H:%M"),
            "horaSalida": row[4].strftime("%H:%M"), "tolerancia": row[5]}


@router.get("")
def listar_horarios(usuario: dict = Depends(usuario_verificado)):
    obtener_rol(usuario["id"])
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('SELECT "id_Horario","Dia_semana","Grupo","Hora_de_entrada","Hora_de_salida","Tolerancia" FROM "Horarios" ORDER BY "Grupo","Dia_semana"')
            return [_salida(row) for row in cur.fetchall()]
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible consultar los horarios.") from error


@router.post("", status_code=201)
def crear_horario(datos: HorarioCrear, usuario: dict = Depends(usuario_verificado)):
    _admin(usuario)
    if not datos.dia_semana.strip() or not datos.grupo.strip():
        raise HTTPException(status_code=422, detail="El día y el grupo son obligatorios.")
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('INSERT INTO "Horarios" ("Dia_semana","Grupo","Hora_de_entrada","Hora_de_salida","Tolerancia") VALUES (%s,%s,%s,%s,%s) RETURNING "id_Horario","Dia_semana","Grupo","Hora_de_entrada","Hora_de_salida","Tolerancia"',
                        (datos.dia_semana.strip(), datos.grupo.strip(), time.fromisoformat(datos.hora_de_entrada), time.fromisoformat(datos.hora_de_salida), datos.tolerancia))
            row = cur.fetchone()
        return _salida(row)
    except PsycopgError as error:
        if getattr(error, "sqlstate", None) == "23505":
            raise HTTPException(status_code=409, detail="Ya existe un horario para ese grupo y día.") from error
        if getattr(error, "sqlstate", None) == "23514":
            raise HTTPException(status_code=422, detail="El horario no cumple las reglas de la base de datos.") from error
        raise HTTPException(status_code=503, detail="No fue posible guardar el horario.") from error


@router.patch("/{id_horario}")
def actualizar_horario(id_horario: int, datos: HorarioActualizar, usuario: dict = Depends(usuario_verificado)):
    _admin(usuario)
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status_code=422, detail="Indica al menos un campo para actualizar.")
    columnas = {"dia_semana": '"Dia_semana"', "grupo": '"Grupo"', "hora_de_entrada": '"Hora_de_entrada"', "hora_de_salida": '"Hora_de_salida"', "tolerancia": '"Tolerancia"'}
    params = []
    sets = []
    for campo, valor in cambios.items():
        sets.append(f"{columnas[campo]}=%s")
        if campo in {"hora_de_entrada", "hora_de_salida"} and valor:
            valor = time.fromisoformat(valor)
        params.append(valor.strip() if isinstance(valor, str) else valor)
    if any(valor is None or (isinstance(valor, str) and not valor.strip()) for valor in cambios.values()):
        raise HTTPException(status_code=422, detail="El día y el grupo no pueden estar vacíos.")
    params.append(id_horario)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('SELECT "Hora_de_entrada","Hora_de_salida" FROM "Horarios" WHERE "id_Horario"=%s', (id_horario,))
            actual = cur.fetchone()
            if actual is None:
                raise HTTPException(status_code=404, detail="Horario no encontrado.")
            entrada = time.fromisoformat(cambios["hora_de_entrada"]) if cambios.get("hora_de_entrada") else actual[0]
            salida = time.fromisoformat(cambios["hora_de_salida"]) if cambios.get("hora_de_salida") else actual[1]
            if entrada >= salida:
                raise HTTPException(status_code=422, detail="La hora de salida debe ser posterior a la entrada.")
            cur.execute('UPDATE "Horarios" SET ' + ','.join(sets) + ' WHERE "id_Horario"=%s RETURNING "id_Horario","Dia_semana","Grupo","Hora_de_entrada","Hora_de_salida","Tolerancia"', params)
            row = cur.fetchone()
        return _salida(row)
    except PsycopgError as error:
        if getattr(error, "sqlstate", None) == "23505":
            raise HTTPException(status_code=409, detail="Ya existe un horario para ese grupo y día.") from error
        if getattr(error, "sqlstate", None) == "23514":
            raise HTTPException(status_code=422, detail="El horario no cumple las reglas de la base de datos.") from error
        raise HTTPException(status_code=503, detail="No fue posible actualizar el horario.") from error


@router.delete("/{id_horario}", status_code=204)
def eliminar_horario(id_horario: int, usuario: dict = Depends(usuario_verificado)):
    _admin(usuario)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('DELETE FROM "Horarios" WHERE "id_Horario"=%s', (id_horario,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Horario no encontrado.")
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible eliminar el horario.") from error
