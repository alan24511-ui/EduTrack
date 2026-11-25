"""Ingesta RFID autenticada del servicio local y registro de asistencia.

Regla derivada del modelo: primera lectura diaria = entrada, segunda = salida;
no se modifica la fila después de tener ambas horas (UNIQUE estudiante/fecha).
"""

import secrets
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from psycopg import Error as PsycopgError

from app.config import obtener_settings
from app.database import obtener_conexion
from app.asistencia_reglas import clasificar_entrada, siguiente_evento
from app.schemas import LecturaRFIDEntrada, RFIDCapturaEntrada, RFIDUIDCaptura
from app.firebase_service import notificar_tutores_estudiante
from app.security import usuario_administrador

router = APIRouter(prefix="/rfid", tags=["Lector RFID"])
ZONA = ZoneInfo("America/Mexico_City")
_eventos_lector = deque(maxlen=50)
_eventos_lector_lock = threading.Lock()
_eventos_lector_id = 0
_bluetooth_status_lock = threading.Lock()
_bluetooth_last_seen: float | None = None
_bluetooth_device_code: str | None = None
_BLUETOOTH_PORT = "/dev/rfcomm0"
_BLUETOOTH_BAUD = 9600
_BLUETOOTH_TIMEOUT_SECONDS = 45
_bluetooth_capture_lock = threading.Lock()
_bluetooth_capture: dict | None = None


def registrar_evento_lector(evento: dict) -> None:
    """Publica el resultado reciente para las pantallas administrativas."""
    global _eventos_lector_id
    with _eventos_lector_lock:
        _eventos_lector_id += 1
        _eventos_lector.append({"id": _eventos_lector_id, **evento})


@router.get("/reader/events")
def eventos_lector(after: int = 0, _: dict = Depends(usuario_administrador)):
    with _eventos_lector_lock:
        return {"lastId": _eventos_lector_id, "eventos": [e for e in _eventos_lector if e["id"] > after]}


@router.get("/reader/status")
def estado_lector(_: dict = Depends(usuario_administrador)):
    with _bluetooth_status_lock:
        ultimo_contacto = _bluetooth_last_seen
    conectado = ultimo_contacto is not None and time.time() - ultimo_contacto <= _BLUETOOTH_TIMEOUT_SECONDS
    with _bluetooth_capture_lock:
        capturando = _bluetooth_capture is not None and not _bluetooth_capture["done"].is_set()
    return {
        "conectado": conectado,
        "estado": "conectado" if conectado else "desconectado",
        "tipo": "Bluetooth HC-05",
        "puerto": _BLUETOOTH_PORT,
        "baud": _BLUETOOTH_BAUD,
        "lectorListo": conectado,
        "capturando": capturando,
        "error": None,
        "ultimoContacto": ultimo_contacto,
        "timeoutSegundos": _BLUETOOTH_TIMEOUT_SECONDS,
    }


@router.post("/reader/associate/{id_estudiante}")
def asociar_desde_lector(id_estudiante: int, datos: RFIDCapturaEntrada, _: dict = Depends(usuario_administrador)):
    """Espera el siguiente UID del HC-05 y lo asocia de forma atómica al alumno."""
    global _bluetooth_capture
    with _bluetooth_status_lock:
        conectado = _bluetooth_last_seen is not None and time.time() - _bluetooth_last_seen <= _BLUETOOTH_TIMEOUT_SECONDS
    if not conectado:
        raise HTTPException(status_code=503, detail="El lector Bluetooth HC-05 no está conectado.")
    capture = {"id": datos.capture_id, "done": threading.Event(), "uid": None, "cancelled": False}
    with _bluetooth_capture_lock:
        if _bluetooth_capture is not None and not _bluetooth_capture["done"].is_set():
            raise HTTPException(status_code=409, detail="Ya hay una lectura RFID en curso.")
        _bluetooth_capture = capture
    try:
        if not capture["done"].wait(60):
            raise HTTPException(status_code=408, detail="No se recibió una tarjeta en 60 segundos.")
        with _bluetooth_capture_lock:
            if capture["cancelled"]:
                raise HTTPException(status_code=409, detail="Lectura cancelada.")
            uid = capture["uid"]
            if _bluetooth_capture is capture:
                _bluetooth_capture = None
        if not uid:
            raise HTTPException(status_code=409, detail="Lectura cancelada.")
        try:
            with obtener_conexion() as conn, conn.cursor() as cur:
                cur.execute('SELECT "Nombre" FROM "Estudiantes" WHERE "Id_Estudiante"=%s FOR UPDATE', (id_estudiante,))
                alumno = cur.fetchone()
                if not alumno:
                    raise HTTPException(status_code=404, detail="El alumno seleccionado ya no existe.")
                cur.execute('SELECT 1 FROM "Credenciales_rfid" WHERE "Id_Estudiante"=%s', (id_estudiante,))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Este alumno ya tiene una tarjeta asociada.")
                cur.execute('INSERT INTO "Credenciales_rfid" ("UID_tarjeta", "Id_Estudiante", "Propietario") VALUES (%s,%s,%s) RETURNING "id_Tarjeta"', (uid, id_estudiante, alumno[0]))
                tarjeta_id = cur.fetchone()[0]
                return {"resultado": "asociada", "uid": uid, "idTarjeta": tarjeta_id, "idEstudiante": id_estudiante, "nombreEstudiante": alumno[0]}
        except PsycopgError as error:
            if getattr(error, "sqlstate", None) == "23505":
                raise HTTPException(status_code=409, detail="UID duplicado o el alumno ya tiene una tarjeta asociada.") from error
            if getattr(error, "sqlstate", None) == "23503":
                raise HTTPException(status_code=404, detail="El alumno no existe.") from error
            raise HTTPException(status_code=503, detail="No fue posible guardar la asociación en PostgreSQL.") from error
    finally:
        with _bluetooth_capture_lock:
            if _bluetooth_capture is capture:
                _bluetooth_capture = None


@router.post("/reader/cancel")
def cancelar_lectura_lector(datos: RFIDCapturaEntrada, _: dict = Depends(usuario_administrador)):
    global _bluetooth_capture
    with _bluetooth_capture_lock:
        capture = _bluetooth_capture
        if not capture or datos.capture_id != capture["id"] or capture["done"].is_set():
            return {"cancelada": False}
        capture["cancelled"] = True
        capture["done"].set()
        return {"cancelada": True}


def _validar_lector(x_reader_token: str):
    esperado = obtener_settings().rfid_ingest_token
    if not esperado:
        raise HTTPException(status_code=503, detail="La ingesta RFID no está configurada.")
    if not secrets.compare_digest(esperado, x_reader_token):
        raise HTTPException(status_code=401, detail="Credencial del lector no válida.")


@router.post("/reader/capture")
def capturar_uid_bluetooth(datos: RFIDUIDCaptura, x_reader_token: str = Header(default="")):
    """Entrega al flujo administrativo el UID recibido por HC-05 si hay captura abierta."""
    _validar_lector(x_reader_token)
    with _bluetooth_status_lock:
        codigo_esperado = _bluetooth_device_code
    if not codigo_esperado or datos.codigo_dispositivo != codigo_esperado:
        raise HTTPException(status_code=403, detail="Lector Bluetooth desconocido o no autorizado.")
    global _bluetooth_capture
    with _bluetooth_capture_lock:
        capture = _bluetooth_capture
        if capture is None or capture["done"].is_set():
            return {"capturada": False}
        capture["uid"] = datos.uid.upper()
        capture["done"].set()
        return {"capturada": True}


@router.post("/heartbeat")
def heartbeat(codigo_dispositivo: str, x_reader_token: str = Header(default=""),
              tipo: str = Query(default="bluetooth")):
    """Actualiza el contacto del lector HC-05 mientras RFCOMM está abierto."""
    _validar_lector(x_reader_token)
    if tipo != "bluetooth":
        raise HTTPException(status_code=422, detail="Tipo de conexión no válido.")
    ahora = datetime.now(ZONA)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('UPDATE "Dispositivos" SET "Ultimo_Contacto"=%s WHERE "Codigo_Dispositivo"=%s AND lower("Estado")=%s RETURNING "Id_Dispositivo"', (ahora, codigo_dispositivo, "activo"))
            if cur.fetchone() is None:
                raise HTTPException(status_code=403, detail="Lector desconocido o inactivo.")
        global _bluetooth_last_seen, _bluetooth_device_code
        with _bluetooth_status_lock:
            _bluetooth_last_seen = time.time()
            _bluetooth_device_code = codigo_dispositivo
        return {"estado": "conectado", "ultimoContacto": ahora.isoformat()}
    except PsycopgError as error:
        raise HTTPException(status_code=503, detail="No fue posible actualizar el estado del lector.") from error


def _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, evento, resultado):
    cur.execute(
        'INSERT INTO "Registros_accesos" ("Fecha_Hora", "Id_Dispositivo", "Id_Estudiante", "Id_Tarjeta", "Tipo_Evento", "Resultado") VALUES (%s,%s,%s,%s,%s,%s)',
        (ahora, id_dispositivo, id_estudiante, id_tarjeta, evento, resultado),
    )


@router.post("/lecturas")
def procesar_lectura(datos: LecturaRFIDEntrada, background_tasks: BackgroundTasks, x_reader_token: str = Header(default="")):
    _validar_lector(x_reader_token)
    uid = datos.uid.upper()
    ahora = datetime.now(ZONA)
    def respuesta(resultado, mensaje, nombre=None, evento=None, hora=None):
        return {
            "resultado": resultado,
            "uid": uid,
            "estudiante": nombre,
            "evento": evento,
            "fecha": ahora.date().isoformat(),
            "hora": hora or ahora.strftime("%H:%M:%S"),
            "mensaje": mensaje,
        }

    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('SELECT "Id_Dispositivo", "Estado" FROM "Dispositivos" WHERE "Codigo_Dispositivo"=%s FOR UPDATE', (datos.codigo_dispositivo,))
            dispositivo = cur.fetchone()
            if not dispositivo or str(dispositivo[1]).lower() != "activo":
                raise HTTPException(status_code=403, detail="Lector desconocido o inactivo.")
            id_dispositivo = dispositivo[0]
            cur.execute('UPDATE "Dispositivos" SET "Ultimo_Contacto"=%s WHERE "Id_Dispositivo"=%s', (ahora, id_dispositivo))

            cur.execute('SELECT c."id_Tarjeta", c."Id_Estudiante", c."Vigencia_inicio", c."Vigencia_termino", e."Nombre", e."Matricula", e."Grupo" FROM "Credenciales_rfid" c LEFT JOIN "Estudiantes" e ON e."Id_Estudiante"=c."Id_Estudiante" WHERE upper(c."UID_tarjeta")=%s', (uid,))
            tarjeta = cur.fetchone()
            if not tarjeta:
                _registrar_acceso(cur, ahora, id_dispositivo, None, None, "lectura", "tarjeta_desconocida")
                return respuesta("TARJETA_NO_REGISTRADA", "La tarjeta no está registrada.")

            id_tarjeta, id_estudiante, inicio, termino, nombre, matricula, grupo = tarjeta
            if inicio and inicio > ahora.date() or termino and termino < ahora.date():
                _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "tarjeta_fuera_de_vigencia")
                return respuesta("TARJETA_DESACTIVADA", "La tarjeta está fuera de su periodo de vigencia.", nombre)
            if nombre is None:
                _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "estudiante_no_encontrado")
                return respuesta("ERROR_PROCESAMIENTO", "No se encontró el alumno asociado.")

            # Serializa por alumno antes del antirrebote: dos lecturas
            # simultáneas no deben convertir la entrada recién creada en salida.
            cur.execute('SELECT "Id_Estudiante" FROM "Estudiantes" WHERE "Id_Estudiante"=%s FOR UPDATE', (id_estudiante,))
            if not cur.fetchone():
                return respuesta("ERROR_PROCESAMIENTO", "No se encontró el alumno asociado.")
            debounce = obtener_settings().rfid_debounce_seconds
            cur.execute(
                'SELECT 1 FROM "Registros_accesos" WHERE "Id_Tarjeta"=%s AND "Fecha_Hora">=%s - (%s * interval \'1 second\') AND "Tipo_Evento" IN (%s, %s) ORDER BY "Fecha_Hora" DESC LIMIT 1',
                (id_tarjeta, ahora, debounce, "entrada", "salida"),
            )
            if cur.fetchone():
                _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "lectura_duplicada")
                return respuesta("LECTURA_DUPLICADA", "Lectura repetida ignorada.", nombre)
            cur.execute('SELECT "id_asistencia", "Hora_Entrada", "Hora_Salida" FROM "Asistencia" WHERE "Id_Estudiante"=%s AND "Fecha"=%s FOR UPDATE', (id_estudiante, ahora.date()))
            asistencia = cur.fetchone()
            entrada = asistencia[1] if asistencia else None
            salida = asistencia[2] if asistencia else None
            siguiente = siguiente_evento(entrada, salida)
            horario = None
            if siguiente == "entrada":
                if not grupo or not grupo.strip():
                    _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "estudiante_sin_grupo")
                    return respuesta("HORARIO_NO_CONFIGURADO", "El estudiante no tiene un grupo asignado.", nombre)
                # El campo de la base puede contener miercoles/miércoles y
                # sabado/sábado. La consulta normaliza lo guardado, así que el
                # valor de comparación también debe ir sin acentos.
                dias = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
                cur.execute(
                    'SELECT "Hora_de_entrada", "Tolerancia" FROM "Horarios" '
                    'WHERE translate(lower("Dia_semana"), \'áéíóú\', \'aeiou\')=%s '
                    'AND lower(btrim("Grupo"))=lower(btrim(%s)) LIMIT 1',
                    (dias[ahora.weekday()], grupo),
                )
                horario = cur.fetchone()
                if horario is None:
                    _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "horario_no_configurado")
                    return respuesta("HORARIO_NO_CONFIGURADO", "No hay horario configurado para el grupo y día de hoy.", nombre)
            if asistencia is None:
                estado = clasificar_entrada(ahora, horario[0], int(horario[1] or 0))
                cur.execute('INSERT INTO "Asistencia" ("Asistencia", "Estado", "Fecha", "Hora_Entrada", "Id_Estudiante") VALUES (TRUE, %s, %s, %s, %s) RETURNING "id_asistencia"', (estado, ahora.date(), ahora, id_estudiante))
                id_asistencia = cur.fetchone()[0]
                evento, resultado = "entrada", "registrada"
            elif siguiente == "entrada":
                id_asistencia = asistencia[0]
                estado = clasificar_entrada(ahora, horario[0], int(horario[1] or 0))
                cur.execute('UPDATE "Asistencia" SET "Asistencia"=TRUE, "Estado"=%s, "Hora_Entrada"=%s WHERE "id_asistencia"=%s', (estado, ahora, id_asistencia))
                evento, resultado = "entrada", "registrada"
            elif siguiente == "salida":
                id_asistencia = asistencia[0]
                cur.execute('UPDATE "Asistencia" SET "Hora_Salida"=%s WHERE "id_asistencia"=%s', (ahora, id_asistencia))
                evento, resultado = "salida", "registrada"
            else:
                _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "asistencia_diaria_completa")
                return respuesta("ASISTENCIA_COMPLETA", "La entrada y salida del día ya están registradas.", nombre)

            _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, evento, resultado)
            if evento == "entrada" and resultado == "registrada":
                tardia = estado == "retardo"
                categoria = "entrada_con_retardo" if tardia else "entrada_registrada"
                titulo = "Entrada con retardo" if tardia else "Entrada registrada"
                texto = f"Se registró la entrada de {nombre} a las {ahora.strftime('%H:%M')}."
                background_tasks.add_task(
                    notificar_tutores_estudiante,
                    id_estudiante,
                    categoria,
                    titulo,
                    texto,
                    f"{categoria}:{id_estudiante}:{ahora.date().isoformat()}",
                )
            tipo = "ENTRADA_REGISTRADA" if evento == "entrada" else "SALIDA_REGISTRADA"
            return respuesta(tipo, f"{evento.capitalize()} registrada para {nombre}.", nombre, evento.upper(), ahora.strftime("%H:%M:%S")) | {"matricula": matricula}
    except PsycopgError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "resultado": "ERROR_PROCESAMIENTO",
                "uid": uid,
                "estudiante": None,
                "evento": None,
                "fecha": ahora.date().isoformat(),
                "hora": ahora.strftime("%H:%M:%S"),
                "mensaje": "No fue posible guardar la lectura.",
            },
        ) from error

