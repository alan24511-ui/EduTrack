"""Ingesta RFID autenticada del servicio local y registro de asistencia.

Regla derivada del modelo: primera lectura diaria = entrada, segunda = salida;
no se modifica la fila después de tener ambas horas (UNIQUE estudiante/fecha).
"""

import secrets
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from psycopg import Error as PsycopgError

from app.config import obtener_settings
from app.database import obtener_conexion
from app.asistencia_reglas import siguiente_evento
from app.schemas import LecturaRFIDEntrada
from app.firebase_service import notificar_tutores_estudiante

router = APIRouter(prefix="/rfid", tags=["Lector RFID"])
ZONA = ZoneInfo("America/Mexico_City")
DEDUP_SEGUNDOS = 4
_lecturas_recientes: dict[tuple[str, str], float] = {}


def _validar_lector(x_reader_token: str):
    esperado = obtener_settings().rfid_ingest_token
    if not esperado:
        raise HTTPException(status_code=503, detail="La ingesta RFID no está configurada.")
    if not secrets.compare_digest(esperado, x_reader_token):
        raise HTTPException(status_code=401, detail="Credencial del lector no válida.")


@router.post("/heartbeat")
def heartbeat(codigo_dispositivo: str, x_reader_token: str = Header(default="")):
    """Actualiza contacto solo mientras el proceso serial está conectado."""
    _validar_lector(x_reader_token)
    ahora = datetime.now(ZONA)
    try:
        with obtener_conexion() as conn, conn.cursor() as cur:
            cur.execute('UPDATE "Dispositivos" SET "Ultimo_Contacto"=%s WHERE "Codigo_Dispositivo"=%s AND lower("Estado")=%s RETURNING "Id_Dispositivo"', (ahora, codigo_dispositivo, "activo"))
            if cur.fetchone() is None:
                raise HTTPException(status_code=403, detail="Lector desconocido o inactivo.")
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
    clave = (datos.codigo_dispositivo, uid)
    tiempo_monotono = time.monotonic()
    if len(_lecturas_recientes) > 1000:
        vencidas = [k for k, v in _lecturas_recientes.items() if tiempo_monotono - v >= DEDUP_SEGUNDOS]
        for k in vencidas:
            _lecturas_recientes.pop(k, None)
    anterior = _lecturas_recientes.get(clave)
    if anterior is not None and tiempo_monotono - anterior < DEDUP_SEGUNDOS:
        return {"resultado": "lectura_duplicada", "mensaje": "Lectura repetida ignorada."}

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
                _lecturas_recientes[clave] = tiempo_monotono
                return {"resultado": "tarjeta_desconocida", "mensaje": "La tarjeta no está registrada."}

            id_tarjeta, id_estudiante, inicio, termino, nombre, matricula, grupo = tarjeta
            if inicio and inicio > ahora.date() or termino and termino < ahora.date():
                _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "tarjeta_fuera_de_vigencia")
                _lecturas_recientes[clave] = tiempo_monotono
                return {"resultado": "tarjeta_vencida", "mensaje": "La tarjeta está fuera de vigencia."}
            if nombre is None:
                _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "estudiante_no_encontrado")
                _lecturas_recientes[clave] = tiempo_monotono
                return {"resultado": "estudiante_no_encontrado", "mensaje": "No se encontró el estudiante asociado."}

            # Durable debounce for repeated scans, including an API process restart.
            cur.execute(
                'SELECT 1 FROM "Registros_accesos" WHERE "Id_Dispositivo"=%s AND "Id_Tarjeta"=%s AND "Fecha_Hora">=%s - interval \'4 seconds\' ORDER BY "Fecha_Hora" DESC LIMIT 1',
                (id_dispositivo, id_tarjeta, ahora),
            )
            if cur.fetchone():
                _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "lectura_duplicada")
                _lecturas_recientes[clave] = tiempo_monotono
                return {"resultado": "lectura_duplicada", "mensaje": "Lectura repetida ignorada.", "estudiante": nombre}

            # Serializa lecturas concurrentes del mismo estudiante.
            cur.execute('SELECT "Id_Estudiante" FROM "Estudiantes" WHERE "Id_Estudiante"=%s FOR UPDATE', (id_estudiante,))
            if not cur.fetchone():
                return {"resultado": "estudiante_no_encontrado", "mensaje": "No se encontró el estudiante asociado."}
            cur.execute('SELECT "id_asistencia", "Hora_Entrada", "Hora_Salida" FROM "Asistencia" WHERE "Id_Estudiante"=%s AND "Fecha"=%s FOR UPDATE', (id_estudiante, ahora.date()))
            asistencia = cur.fetchone()
            entrada = asistencia[1] if asistencia else None
            salida = asistencia[2] if asistencia else None
            siguiente = siguiente_evento(entrada, salida)
            if asistencia is None:
                cur.execute('INSERT INTO "Asistencia" ("Asistencia", "Estado", "Fecha", "Hora_Entrada", "Id_Estudiante") VALUES (TRUE, %s, %s, %s, %s) RETURNING "id_asistencia"', ("presente", ahora.date(), ahora, id_estudiante))
                id_asistencia = cur.fetchone()[0]
                evento, resultado = "entrada", "registrada"
            elif siguiente == "entrada":
                id_asistencia = asistencia[0]
                cur.execute('UPDATE "Asistencia" SET "Asistencia"=TRUE, "Estado"=%s, "Hora_Entrada"=%s WHERE "id_asistencia"=%s', ("presente", ahora, id_asistencia))
                evento, resultado = "entrada", "registrada"
            elif siguiente == "salida":
                id_asistencia = asistencia[0]
                cur.execute('UPDATE "Asistencia" SET "Hora_Salida"=%s WHERE "id_asistencia"=%s', (ahora, id_asistencia))
                evento, resultado = "salida", "registrada"
            else:
                _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, "lectura", "asistencia_diaria_completa")
                _lecturas_recientes[clave] = tiempo_monotono
                return {"resultado": "lectura_duplicada", "mensaje": "La entrada y salida del día ya están registradas.", "estudiante": nombre}

            _registrar_acceso(cur, ahora, id_dispositivo, id_estudiante, id_tarjeta, evento, resultado)
            _lecturas_recientes[clave] = tiempo_monotono
            if evento == "entrada" and resultado == "registrada":
                dias = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
                cur.execute(
                    'SELECT "Hora_de_entrada", "Tolerancia" FROM "Horarios" '
                    'WHERE translate(lower("Dia_semana"), \'áéíóú\', \'aeiou\')=%s '
                    'AND lower("Grupo")=lower(%s) LIMIT 1',
                    (dias[ahora.weekday()], grupo),
                )
                horario = cur.fetchone()
                tardia = bool(horario and ahora.time().replace(tzinfo=None) > (
                    datetime.combine(ahora.date(), horario[0]) + timedelta(minutes=int(horario[1] or 0))
                ).time())
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
            return {"resultado": resultado, "evento": evento, "estudiante": nombre, "matricula": matricula, "fechaHora": ahora.isoformat()}
    except PsycopgError as error:
        # Retire cache entry so a failed database transaction can be retried.
        _lecturas_recientes.pop(clave, None)
        raise HTTPException(status_code=503, detail="No fue posible guardar la lectura.") from error

