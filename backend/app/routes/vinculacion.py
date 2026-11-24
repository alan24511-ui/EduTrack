"""Búsqueda y asociación segura de estudiantes para la cuenta tutor autenticada."""

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.schemas import ConfirmacionVinculacionEntrada
from app.security import obtener_rol, usuario_verificado

router = APIRouter(prefix="/vinculacion", tags=["Vinculación"])


def _obtener_id_tutor(auth_user_id: str) -> int:
    with obtener_conexion() as conexion, conexion.cursor() as cursor:
        cursor.execute(
            'SELECT "Id_Tutor" FROM "Tutores" WHERE auth_user_id=%s ORDER BY "Id_Tutor" LIMIT 1',
            (auth_user_id,),
        )
        fila = cursor.fetchone()
    if fila is None:
        raise HTTPException(status_code=403, detail="Tu cuenta todavía no está registrada como tutor.")
    return fila[0]


def _validar_tutor(usuario: dict) -> int:
    if obtener_rol(usuario["id"]) != "tutor":
        raise HTTPException(status_code=403, detail="Esta operación es exclusiva para tutores.")
    return _obtener_id_tutor(usuario["id"])


@router.get("/buscar", summary="Buscar estudiantes para vincular")
def buscar_estudiantes(
    q: str = Query(default="", max_length=120),
    grupo: str | None = Query(default=None, max_length=80),
    usuario: dict = Depends(usuario_verificado),
):
    id_tutor = _validar_tutor(usuario)
    termino = q.strip()
    filtro_grupo = grupo.strip() if grupo and grupo.strip() else ""
    if len(termino) < 2:
        termino = ""
    if not termino and not filtro_grupo:
        return {"grupos": [], "estudiantes": []}

    filtros = []
    parametros: list = []
    if termino:
        filtros.append('(e."Nombre" ILIKE %s OR e."Matricula" ILIKE %s)')
        patron = f"%{termino}%"
        parametros.extend([patron, patron])
    if filtro_grupo:
        filtros.append('e."Grupo"=%s')
        parametros.append(filtro_grupo)

    try:
        with obtener_conexion() as conexion, conexion.cursor() as cursor:
            cursor.execute('SELECT DISTINCT "Grupo" FROM "Estudiantes" WHERE "Grupo" IS NOT NULL AND btrim("Grupo") <> \'\' ORDER BY "Grupo"')
            grupos = [fila[0] for fila in cursor.fetchall()]
            cursor.execute(
                'SELECT e."Id_Estudiante",e."Nombre",e."Matricula",e."Grupo" '
                'FROM "Estudiantes" e WHERE ' + " AND ".join(filtros) +
                ' AND NOT EXISTS (SELECT 1 FROM "Estudiante_Tutor" et '
                'WHERE et."Id_Estudiante"=e."Id_Estudiante" AND et."Id_Tutor"=%s) '
                'ORDER BY e."Nombre" LIMIT 20',
                [*parametros, id_tutor],
            )
            filas = cursor.fetchall()
        return {
            "grupos": grupos,
            "estudiantes": [
                {"id": fila[0], "nombre": fila[1], "matricula": fila[2], "grupo": fila[3]}
                for fila in filas
            ],
        }
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible buscar estudiantes.") from error


@router.post("/confirmar", summary="Confirmar la asociación de un estudiante")
def confirmar_vinculacion(
    datos: ConfirmacionVinculacionEntrada,
    usuario: dict = Depends(usuario_verificado),
):
    id_tutor = _validar_tutor(usuario)
    try:
        with obtener_conexion() as conexion, conexion.cursor() as cursor:
            # Serializa asociaciones idénticas si no existe una restricción UNIQUE en Supabase.
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"Estudiante_Tutor:{datos.id_estudiante}:{id_tutor}",),
            )
            cursor.execute(
                'SELECT 1 FROM "Estudiante_Tutor" WHERE "Id_Estudiante"=%s AND "Id_Tutor"=%s',
                (datos.id_estudiante, id_tutor),
            )
            if cursor.fetchone() is not None:
                raise HTTPException(status_code=409, detail="Este estudiante ya está vinculado a tu cuenta.")

            cursor.execute(
                'SELECT 1 FROM "Estudiantes" WHERE "Id_Estudiante"=%s FOR UPDATE',
                (datos.id_estudiante,),
            )
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="No se encontró el estudiante seleccionado.")

            cursor.execute(
                'INSERT INTO "Estudiante_Tutor" '
                '("Id_Estudiante","Id_Tutor","Parentesco","Autorizado") VALUES (%s,%s,%s,TRUE)',
                (datos.id_estudiante, id_tutor, datos.parentesco.strip()),
            )
        return {"mensaje": "Estudiante vinculado correctamente."}
    except HTTPException:
        raise
    except PsycopgError as error:
        if getattr(error, "sqlstate", None) == "23505":
            raise HTTPException(status_code=409, detail="Este estudiante ya está vinculado a tu cuenta.") from error
        raise HTTPException(status_code=503, detail="No fue posible vincular al estudiante.") from error
