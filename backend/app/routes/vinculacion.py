"""Endpoints de vinculación estudiante <-> tutor mediante código de un solo uso.

Reglas aplicadas:
- El id del estudiante y del tutor se resuelven siempre en el servidor.
- Solo se guarda el hash del código (sha256).
- El código expira y no puede reutilizarse.
- Un estudiante no puede tener más de un tutor vinculado.
- El consumo del código y la inserción en "Estudiante_Tutor" ocurren en una
  misma transacción.
"""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Error as PsycopgError

from app.codigos import generar_codigo, hashear_codigo, normalizar_codigo
from app.config import obtener_settings
from app.database import obtener_conexion
from app.schemas import ConfirmacionVinculacionEntrada, ConsultaCodigoEntrada, GenerarCodigoEntrada
from app.security import usuario_verificado

router = APIRouter(prefix="/vinculacion", tags=["Vinculación"])


def _es_administrador(auth_user_id: str) -> bool:
    try:
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    'SELECT 1 FROM "Administradores" WHERE auth_user_id = %s',
                    (auth_user_id,),
                )
                return cursor.fetchone() is not None
    except PsycopgError:
        raise HTTPException(
            status_code=500,
            detail=(
                'No se pudo comprobar si la cuenta es administrador '
                '("Administradores" no existe o no es accesible).'
            ),
        )


def _verificar_puede_generar_codigos(auth_user_id: str) -> None:
    if not obtener_settings().vinculacion_generacion_solo_admin:
        return
    if not _es_administrador(auth_user_id):
        raise HTTPException(
            status_code=403,
            detail="Solo un administrador puede generar códigos de vinculación.",
        )


def _obtener_id_tutor(auth_user_id: str) -> int:
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                'SELECT "Id_Tutor" FROM "Tutores" WHERE auth_user_id = %s',
                (auth_user_id,),
            )
            fila = cursor.fetchone()
    if fila is None:
        raise HTTPException(
            status_code=403,
            detail="Tu cuenta todavía no está registrada como tutor.",
        )
    return fila[0]


@router.post("/codigos", summary="Generar un código de vinculación (administrador)")
def generar_codigo_vinculacion(
    datos: GenerarCodigoEntrada,
    usuario: dict = Depends(usuario_verificado),
):
    _verificar_puede_generar_codigos(usuario["id"])

    minutos = obtener_settings().vinculacion_codigo_expiracion_minutos
    matricula = datos.matricula.strip()

    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                'SELECT "Id_Estudiante" FROM "Estudiantes" WHERE "Matricula" = %s',
                (matricula,),
            )
            fila = cursor.fetchone()
            if fila is None:
                raise HTTPException(
                    status_code=404,
                    detail="No existe un estudiante con esa matrícula.",
                )
            id_estudiante = fila[0]

            codigo = generar_codigo()
            cursor.execute(
                'INSERT INTO "Codigos_vinculacion" '
                "(id_estudiante, codigo_hash, fecha_expiracion, utilizado, fecha_creacion) "
                "VALUES (%s, %s, now() + make_interval(mins => %s::int), FALSE, now()) "
                "RETURNING id_codigo, fecha_expiracion",
                (id_estudiante, hashear_codigo(codigo), minutos),
            )
            nueva = cursor.fetchone()
        conexion.commit()

    return {
        "codigo": codigo,
        "matricula": matricula,
        "id_codigo": nueva[0],
        "fecha_expiracion": nueva[1],
        "mensaje": "Comparte este código con el tutor. Solo se muestra una vez.",
    }


@router.post("/consultar", summary="Consultar un código de vinculación")
def consultar_codigo(
    datos: ConsultaCodigoEntrada,
    usuario: dict = Depends(usuario_verificado),
):
    _obtener_id_tutor(usuario["id"])

    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT c.utilizado, (c.fecha_expiracion <= now()) AS expirado, "
                'e."Nombre", e."Grupo", e."Matricula" '
                'FROM "Codigos_vinculacion" c '
                'JOIN "Estudiantes" e ON e."Id_Estudiante" = c.id_estudiante '
                "WHERE c.codigo_hash = %s",
                (hashear_codigo(normalizar_codigo(datos.codigo)),),
            )
            fila = cursor.fetchone()

    if fila is None:
        raise HTTPException(status_code=404, detail="El código no es válido.")
    utilizado, expirado, nombre, grupo, matricula = fila
    if utilizado:
        raise HTTPException(status_code=409, detail="El código ya fue utilizado.")
    if expirado:
        raise HTTPException(status_code=410, detail="El código ya expiró.")

    # Solo se devuelve la información mínima para que el tutor confirme.
    return {"estudiante": {"nombre": nombre, "grupo": grupo, "matricula": matricula}}


@router.post("/confirmar", summary="Confirmar la vinculación del estudiante")
def confirmar_vinculacion(
    datos: ConfirmacionVinculacionEntrada,
    usuario: dict = Depends(usuario_verificado),
):
    id_tutor = _obtener_id_tutor(usuario["id"])
    hash_codigo = hashear_codigo(normalizar_codigo(datos.codigo))

    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            # Bloquea la fila del código para evitar consumos simultáneos.
            cursor.execute(
                "SELECT id_codigo, id_estudiante, utilizado, "
                "(fecha_expiracion <= now()) AS expirado "
                'FROM "Codigos_vinculacion" WHERE codigo_hash = %s FOR UPDATE',
                (hash_codigo,),
            )
            fila = cursor.fetchone()
            if fila is None:
                raise HTTPException(status_code=404, detail="El código no es válido.")

            id_codigo, id_estudiante, utilizado, expirado = fila
            if utilizado:
                raise HTTPException(status_code=409, detail="El código ya fue utilizado.")
            if expirado:
                raise HTTPException(status_code=410, detail="El código ya expiró.")

            cursor.execute(
                'SELECT 1 FROM "Estudiante_Tutor" WHERE "Id_Estudiante" = %s',
                (id_estudiante,),
            )
            if cursor.fetchone() is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Este estudiante ya tiene un tutor vinculado.",
                )

            try:
                cursor.execute(
                    'INSERT INTO "Estudiante_Tutor" '
                    '("Id_Estudiante", "Id_Tutor", "Parentesco", "Autorizado") '
                    "VALUES (%s, %s, %s, TRUE)",
                    (id_estudiante, id_tutor, datos.parentesco),
                )
            except PsycopgError:
                raise HTTPException(
                    status_code=409,
                    detail="No fue posible vincular al estudiante.",
                )

            cursor.execute(
                'UPDATE "Codigos_vinculacion" SET utilizado = TRUE, fecha_utilizacion = now() '
                "WHERE id_codigo = %s AND utilizado = FALSE",
                (id_codigo,),
            )
            if cursor.rowcount != 1:
                raise HTTPException(status_code=409, detail="El código ya fue utilizado.")

        conexion.commit()

    return {"mensaje": "Estudiante vinculado correctamente.", "idTutor": id_tutor}
