"""Endpoints de autenticación de tutores.

Flujo:
1. POST /auth/register-tutor  -> crea la cuenta en Supabase Auth (envía OTP al correo).
2. POST /auth/verify-otp      -> verifica el OTP y crea el registro en "Tutores".
3. POST /auth/login           -> inicia sesión.
4. GET  /auth/me              -> perfil del tutor autenticado.
5. POST /auth/logout          -> cierra la sesión en Supabase Auth.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg import Error as PsycopgError

from app.database import obtener_conexion
from app.schemas import (CambiarPasswordEntrada, CorreoEntrada, LoginEntrada, RecuperacionPasswordEntrada,
                         RegistroTutorEntrada, RenovacionSesionEntrada,
                         ReenvioOTPEntrada, TutorActualizar, VerificacionOTPEntrada)
from app.security import obtener_rol, usuario_actual, usuario_verificado
from app import supabase_auth

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _buscar_tutor_por_auth_id(auth_user_id: str) -> dict | None:
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                'SELECT "Id_Tutor", "Nombre", "Telefono", "Correo" '
                'FROM "Tutores" WHERE auth_user_id = %s',
                (auth_user_id,),
            )
            fila = cursor.fetchone()
    if fila is None:
        return None
    return {
        "idTutor": fila[0],
        "nombre": fila[1],
        "telefono": fila[2],
        "correo": fila[3],
    }


def _crear_tutor_si_no_existe(auth_user_id: str, nombre: str, correo: str) -> dict:
    """Inserta el tutor asociado al usuario de Supabase (idempotente)."""
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            # The supplied schema has no UNIQUE constraint on Tutores.auth_user_id.
            # Serialize this operation without assuming or altering that schema.
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (auth_user_id,))
            cursor.execute(
                'SELECT "Id_Tutor", "Nombre", "Telefono", "Correo" FROM "Tutores" WHERE auth_user_id=%s ORDER BY "Id_Tutor" LIMIT 1',
                (auth_user_id,),
            )
            fila = cursor.fetchone()
            if fila is None:
                cursor.execute(
                    'INSERT INTO "Tutores" ("Nombre", "Correo", auth_user_id) VALUES (%s,%s,%s) RETURNING "Id_Tutor", "Nombre", "Telefono", "Correo"',
                    (nombre, correo, auth_user_id),
                )
                fila = cursor.fetchone()
        conexion.commit()

    if fila is None:
        raise HTTPException(
            status_code=500,
            detail="No fue posible registrar al tutor en la base de datos.",
        )
    return {"idTutor": fila[0], "nombre": fila[1], "telefono": fila[2], "correo": fila[3]}


def _tiene_estudiante_vinculado(id_tutor: int) -> bool:
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                'SELECT 1 FROM "Estudiante_Tutor" WHERE "Id_Tutor" = %s',
                (id_tutor,),
            )
            return cursor.fetchone() is not None


def _sesion_desde_respuesta(resultado: dict) -> dict:
    return {
        "access_token": resultado.get("access_token"),
        "refresh_token": resultado.get("refresh_token"),
        "expires_in": resultado.get("expires_in"),
        "token_type": resultado.get("token_type", "bearer"),
    }


@router.post("/register-tutor", summary="Registrar un tutor")
def registrar_tutor(datos: RegistroTutorEntrada):
    resultado = supabase_auth.registrar_usuario(datos.correo, datos.password, datos.nombre)
    usuario = resultado.get("user", resultado)

    return {
        "mensaje": "Cuenta creada. Revisa tu correo e introduce el código de verificación.",
        "requiere_verificacion": True,
        "correo": datos.correo,
        "usuario_id": usuario.get("id"),
    }


@router.post("/verify-otp", summary="Verificar el código OTP y registrar al tutor")
def verificar_otp(datos: VerificacionOTPEntrada):
    resultado = supabase_auth.verificar_otp(datos.correo, datos.token)
    usuario = resultado.get("user") or {}
    auth_user_id = usuario.get("id")
    if not auth_user_id:
        raise HTTPException(status_code=400, detail="No fue posible verificar el código.")

    nombre = (usuario.get("user_metadata") or {}).get("nombre") or datos.correo
    try:
        tutor = _crear_tutor_si_no_existe(auth_user_id, nombre, datos.correo)
    except PsycopgError:
        raise HTTPException(
            status_code=500,
            detail="El correo se verificó, pero no se pudo registrar al tutor.",
        )

    return {
        "mensaje": "Correo verificado correctamente.",
        "sesion": _sesion_desde_respuesta(resultado),
        "tutor": tutor,
    }


@router.post("/resend-otp", summary="Reenviar OTP de registro o recuperación")
def reenviar_codigo(datos: ReenvioOTPEntrada):
    supabase_auth.reenviar_otp(datos.correo, datos.tipo)
    return {"mensaje": "Si la solicitud es válida, se enviará un nuevo código."}


@router.post("/recover", summary="Solicitar recuperación de contraseña")
def recuperar_password(datos: CorreoEntrada):
    # Respuesta neutra para no revelar si el correo tiene una cuenta.
    supabase_auth.solicitar_recuperacion(datos.correo)
    return {"mensaje": "Si la cuenta existe, recibirás instrucciones por correo."}


@router.post("/reset-password", summary="Verificar OTP y establecer contraseña nueva")
def restablecer_password(datos: RecuperacionPasswordEntrada):
    sesion = supabase_auth.verificar_otp(datos.correo, datos.token, tipo="recovery")
    access_token = sesion.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No fue posible verificar el código.")
    supabase_auth.actualizar_password(access_token, datos.nueva_password)
    return {"mensaje": "Contraseña actualizada. Ya puedes iniciar sesión."}


@router.post("/refresh", summary="Renovar sesión")
def renovar(datos: RenovacionSesionEntrada):
    resultado = supabase_auth.renovar_sesion(datos.refresh_token)
    usuario = resultado.get("user") or {}
    return {"sesion": _sesion_desde_respuesta(resultado), "usuario_id": usuario.get("id")}


@router.post("/login", summary="Iniciar sesión")
def iniciar_sesion(datos: LoginEntrada):
    resultado = supabase_auth.iniciar_sesion(datos.correo, datos.password)
    usuario = resultado.get("user") or {}
    if not usuario.get("email_confirmed_at"):
        raise HTTPException(
            status_code=403,
            detail="Debes verificar tu correo electrónico antes de iniciar sesión.",
        )

    auth_user_id = usuario.get("id", "")
    nombre = (usuario.get("user_metadata") or {}).get("nombre") or datos.correo

    try:
        rol = obtener_rol(auth_user_id)
        if rol == "tutor":
            tutor = _crear_tutor_si_no_existe(auth_user_id, nombre, datos.correo)
            requiere_vinculacion = not _tiene_estudiante_vinculado(tutor["idTutor"])
        else:
            tutor = None
            requiere_vinculacion = False
    except PsycopgError:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar los datos del tutor.",
        )

    return {
        "sesion": _sesion_desde_respuesta(resultado),
        "tutor": tutor,
        "requiere_vinculacion": requiere_vinculacion,
        "rol": rol,
    }


@router.get("/me", summary="Perfil del tutor autenticado")
def perfil(usuario: dict = Depends(usuario_verificado)):
    try:
        rol = obtener_rol(usuario["id"])
        tutor = _buscar_tutor_por_auth_id(usuario["id"]) if rol == "tutor" else None
    except PsycopgError:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar los datos del tutor.",
        )
    return {"tutor": tutor, "rol": rol}


@router.patch("/me", summary="Actualizar el perfil del tutor autenticado")
def actualizar_perfil(datos: TutorActualizar, usuario: dict = Depends(usuario_verificado)):
    if obtener_rol(usuario["id"]) != "tutor":
        raise HTTPException(status_code=403, detail="Esta operación es exclusiva para tutores.")
    if not datos.nombre.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio.")
    try:
        with obtener_conexion() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                'UPDATE "Tutores" SET "Nombre"=%s, "Telefono"=%s WHERE auth_user_id=%s '
                'RETURNING "Id_Tutor", "Nombre", "Telefono", "Correo"',
                (datos.nombre.strip(), datos.telefono.strip() if datos.telefono else None, usuario["id"]),
            )
            fila = cursor.fetchone()
            if fila is None:
                raise HTTPException(status_code=404, detail="No se encontró el perfil del tutor.")
        return {"idTutor": fila[0], "nombre": fila[1], "telefono": fila[2], "correo": fila[3]}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible actualizar el perfil.") from error


@router.post("/me/password", summary="Cambiar la contraseña de la cuenta")
def cambiar_password(datos: CambiarPasswordEntrada, usuario: dict = Depends(usuario_verificado),
                     authorization: str = Header(default="")):
    # No se aceptan correos/identidades enviados por el cliente para elegir la cuenta.
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Falta el token de acceso.")
    supabase_auth.actualizar_password(authorization.split(" ", 1)[1].strip(), datos.nueva_password)
    return {"mensaje": "Contraseña actualizada correctamente."}


@router.post("/logout", summary="Cerrar sesión")
def cerrar_sesion(
    usuario: dict = Depends(usuario_actual),
    authorization: str = Header(default=""),
):
    token = authorization.split(" ", 1)[1].strip()
    supabase_auth.cerrar_sesion(token)
    return {"mensaje": "Sesión cerrada correctamente."}
