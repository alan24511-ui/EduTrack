"""Consulta y administración de estudiantes con aislamiento por tutor."""

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.schemas import EstudianteActualizar, EstudianteCrear
from app.security import obtener_rol, usuario_administrador, usuario_verificado

router = APIRouter(prefix="/estudiantes", tags=["Estudiantes"])


def _traducir_error_db(error: PsycopgError):
    if getattr(error, "sqlstate", None) == "23505":
        raise HTTPException(status_code=409, detail="La matrícula o correo ya está registrado.") from error
    if getattr(error, "sqlstate", None) == "23503":
        raise HTTPException(status_code=404, detail="El estudiante relacionado no existe.") from error
    raise HTTPException(status_code=500, detail="No fue posible completar la operación.") from error


def _estudiante(fila):
    return {"id": fila[0], "nombre": fila[1], "matricula": fila[2], "grupo": fila[3], "correoInstitucional": fila[4]}


@router.get("")
def listar_estudiantes(
    q: str = Query(default="", max_length=120),
    grupo: str | None = Query(default=None, max_length=80),
    usuario: dict = Depends(usuario_verificado),
):
    rol = obtener_rol(usuario["id"])
    filtros = []
    parametros: list = []
    if rol == "tutor":
        filtros.append('EXISTS (SELECT 1 FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" WHERE et."Id_Estudiante"=e."Id_Estudiante" AND et."Autorizado"=TRUE AND t.auth_user_id=%s)')
        parametros.append(usuario["id"])
    elif rol not in {"administrador", "superadministrador"}:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    if q.strip():
        filtros.append('(e."Nombre" ILIKE %s OR e."Matricula" ILIKE %s)')
        patron = f"%{q.strip()}%"
        parametros.extend([patron, patron])
    if grupo:
        filtros.append('e."Grupo" = %s')
        parametros.append(grupo.strip())
    where = " WHERE " + " AND ".join(filtros) if filtros else ""
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('SELECT e."Id_Estudiante", e."Nombre", e."Matricula", e."Grupo", e."Correo_Institucional" FROM "Estudiantes" e' + where + ' ORDER BY e."Nombre"', parametros)
            filas = cur.fetchall()
            ids = [row[0] for row in filas]
            tutores: dict[int, list[dict]] = {id_est: [] for id_est in ids}
            if ids:
                cur.execute('SELECT et."Id_Estudiante", t."Id_Tutor", t."Nombre", et."Parentesco", et."Autorizado" FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" WHERE et."Id_Estudiante" = ANY(%s)', (ids,))
                for id_est, id_tutor, nombre, parentesco, autorizado in cur.fetchall():
                    tutores[id_est].append({"idTutor": id_tutor, "nombre": nombre, "parentesco": parentesco, "autorizado": autorizado})
        return [{**_estudiante(f), "tutores": tutores[f[0]]} for f in filas]
    except PsycopgError as error:
        _traducir_error_db(error)


@router.get("/{id_estudiante}")
def obtener_estudiante(id_estudiante: int, usuario: dict = Depends(usuario_verificado)):
    rol = obtener_rol(usuario["id"])
    consulta = 'SELECT e."Id_Estudiante", e."Nombre", e."Matricula", e."Grupo", e."Correo_Institucional" FROM "Estudiantes" e'
    params: list = [id_estudiante]
    where = ' WHERE e."Id_Estudiante"=%s'
    if rol == "tutor":
        where += ' AND EXISTS (SELECT 1 FROM "Estudiante_Tutor" et JOIN "Tutores" t ON t."Id_Tutor"=et."Id_Tutor" WHERE et."Id_Estudiante"=e."Id_Estudiante" AND et."Autorizado"=TRUE AND t.auth_user_id=%s)'
        params.append(usuario["id"])
    elif rol not in {"administrador", "superadministrador"}:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute(consulta + where, params)
            fila = cur.fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
        return _estudiante(fila)
    except PsycopgError as error:
        _traducir_error_db(error)


@router.post("", status_code=201)
def crear_estudiante(datos: EstudianteCrear, _: dict = Depends(usuario_administrador)):
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('INSERT INTO "Estudiantes" ("Nombre", "Matricula", "Grupo", "Correo_Institucional") VALUES (%s,%s,%s,%s) RETURNING "Id_Estudiante", "Nombre", "Matricula", "Grupo", "Correo_Institucional"', (datos.nombre.strip(), datos.matricula.strip(), datos.grupo.strip(), str(datos.correo_institucional) if datos.correo_institucional else None))
            fila = cur.fetchone()
        return _estudiante(fila)
    except PsycopgError as error:
        _traducir_error_db(error)


@router.patch("/{id_estudiante}")
def actualizar_estudiante(id_estudiante: int, datos: EstudianteActualizar, _: dict = Depends(usuario_administrador)):
    cambios = datos.model_dump(exclude_unset=True, exclude_none=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="Indica al menos un campo para actualizar.")
    columnas = {"nombre": '"Nombre"', "matricula": '"Matricula"', "grupo": '"Grupo"', "correo_institucional": '"Correo_Institucional"'}
    sets, params = [], []
    for campo, valor in cambios.items():
        sets.append(f"{columnas[campo]}=%s")
        params.append(str(valor).strip() if isinstance(valor, str) else valor)
    params.append(id_estudiante)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('UPDATE "Estudiantes" SET ' + ",".join(sets) + ' WHERE "Id_Estudiante"=%s RETURNING "Id_Estudiante", "Nombre", "Matricula", "Grupo", "Correo_Institucional"', params)
            fila = cur.fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
        return _estudiante(fila)
    except PsycopgError as error:
        _traducir_error_db(error)
