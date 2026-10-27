
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg import Error as PsycopgError
from psycopg import errors
from psycopg.rows import dict_row

from app.database import obtener_conexion


# =========================================================
# CONFIGURACIÓN DE LA API
# =========================================================

app = FastAPI(
    title="EduTrack API",
    description="API para el sistema escolar de control de acceso y asistencia.",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# MODELOS
# =========================================================

class NuevoEstudiante(BaseModel):
    Matricula: str = Field(min_length=1, max_length=50)
    Nombre: str = Field(min_length=1, max_length=150)
    Grupo: str = Field(min_length=1, max_length=50)
    Correo_Institucional: str | None = Field(
        default=None,
        max_length=254,
    )


class LecturaTarjeta(BaseModel):
    uid: str


# =========================================================
# ESTADO Y CONEXIÓN CON LA BASE DE DATOS
# =========================================================

@app.get("/health", tags=["Estado"])
def health_check():
    return {
        "status": "ok",
        "message": "EduTrack API funcionando correctamente",
    }


@app.get("/health/db", tags=["Estado"])
def verificar_base_datos():
    try:
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return {
            "status": "ok",
            "database": "connected",
            "message": "Conexión con PostgreSQL exitosa",
        }

    except PsycopgError as error:
        print(f"ERROR DE CONEXIÓN CON LA BASE DE DATOS: {error}")

        raise HTTPException(
            status_code=503,
            detail="No fue posible conectar con PostgreSQL.",
        )


# =========================================================
# CONSULTAR ESTUDIANTES
# =========================================================

@app.get("/estudiantes", tags=["Estudiantes"])
def obtener_estudiantes():
    try:
        with obtener_conexion() as conexion:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        "Id_Estudiante",
                        "Matricula",
                        "Nombre",
                        "Grupo",
                        "Correo_Institucional"
                    FROM public."Estudiantes"
                    ORDER BY "Id_Estudiante" ASC
                    """
                )

                estudiantes = cursor.fetchall()

        return estudiantes

    except PsycopgError as error:
        print(f"ERROR AL CONSULTAR ESTUDIANTES: {error}")

        raise HTTPException(
            status_code=503,
            detail="No fue posible consultar los estudiantes.",
        )


# =========================================================
# CONTAR ESTUDIANTES
# =========================================================

@app.get("/estudiantes/count", tags=["Estudiantes"])
def contar_estudiantes():
    try:
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM public."Estudiantes"
                    """
                )

                total = cursor.fetchone()[0]

        return {"total": total}

    except PsycopgError as error:
        print(f"ERROR AL CONTAR ESTUDIANTES: {error}")

        raise HTTPException(
            status_code=503,
            detail="No fue posible contar los estudiantes.",
        )


# =========================================================
# REGISTRAR ESTUDIANTE
# =========================================================

@app.post(
    "/estudiantes",
    tags=["Estudiantes"],
    status_code=201,
)
def crear_estudiante(estudiante: NuevoEstudiante):
    matricula = estudiante.Matricula.strip()
    nombre = estudiante.Nombre.strip()
    grupo = estudiante.Grupo.strip()

    correo = estudiante.Correo_Institucional
    correo = correo.strip() if correo else None

    # Validar campos obligatorios.
    if not matricula or not nombre or not grupo:
        raise HTTPException(
            status_code=422,
            detail="Matrícula, nombre y grupo son obligatorios.",
        )

    # Convertir un correo vacío en NULL.
    if correo == "":
        correo = None

    try:
        with obtener_conexion() as conexion:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO public."Estudiantes"
                    (
                        "Matricula",
                        "Nombre",
                        "Grupo",
                        "Correo_Institucional"
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING
                        "Id_Estudiante",
                        "Matricula",
                        "Nombre",
                        "Grupo",
                        "Correo_Institucional"
                    """,
                    (
                        matricula,
                        nombre,
                        grupo,
                        correo,
                    ),
                )

                nuevo_estudiante = cursor.fetchone()

        return nuevo_estudiante

    except errors.UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail=(
                "La matrícula o el correo institucional "
                "ya están registrados."
            ),
        )

    except PsycopgError as error:
        print(f"ERROR AL REGISTRAR ESTUDIANTE: {error}")

        raise HTTPException(
            status_code=503,
            detail="No fue posible registrar el estudiante.",
        )


# =========================================================
# ELIMINAR ESTUDIANTE
# =========================================================

@app.delete(
    "/estudiantes/{id}",
    tags=["Estudiantes"],
)
def eliminar_estudiante(id: int):
    if id <= 0:
        raise HTTPException(
            status_code=422,
            detail="El identificador debe ser positivo.",
        )

    try:
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM public."Estudiantes"
                    WHERE "Id_Estudiante" = %s
                    RETURNING "Id_Estudiante"
                    """,
                    (id,),
                )

                eliminado = cursor.fetchone()

                if eliminado is None:
                    raise HTTPException(
                        status_code=404,
                        detail="El estudiante no existe.",
                    )

        return {
            "message": "Estudiante eliminado correctamente."
        }

    except HTTPException:
        raise

    except PsycopgError as error:
        print(f"ERROR AL ELIMINAR ESTUDIANTE: {error}")

        raise HTTPException(
            status_code=409,
            detail=(
                "No fue posible eliminar el estudiante. "
                "Puede tener registros relacionados."
            ),
        )


# =========================================================
# SIMULADOR DE LECTURA DE TARJETAS
# =========================================================

TARJETAS_DE_PRUEBA = {
    "A1B2C3D4",
}


@app.post("/device/scan", tags=["Dispositivos"])
def escanear_tarjeta(lectura: LecturaTarjeta):
    uid = lectura.uid.strip().upper()

    if not uid or len(uid) > 64:
        raise HTTPException(
            status_code=422,
            detail="El UID no es válido.",
        )

    if uid not in TARJETAS_DE_PRUEBA:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "unknown",
                "uid": uid,
                "message": "Tarjeta no registrada",
            },
        )

    return {
        "status": "recognized",
        "uid": uid,
        "message": "Tarjeta reconocida correctamente",
    }
