"""Puente USB serie -> HTTP FastAPI. No se conecta a PostgreSQL/Supabase."""

import argparse
import logging
import os
import time

import requests
import serial
from serial.tools import list_ports

from protocol import parse_uid_line

LOG = logging.getLogger("edutrack-reader")


def elegir_puerto(configurado: str | None) -> str:
    if configurado:
        return configurado
    puertos = [p.device for p in list_ports.comports()]
    if len(puertos) != 1:
        raise RuntimeError("Configura --port; no se pudo elegir un puerto USB sin ambigüedad.")
    return puertos[0]


def ejecutar(puerto: str, velocidad: int, endpoint: str, cooldown: float, codigo_dispositivo: str, token: str) -> None:
    ultimo_uid = None
    ultima_envio = 0.0
    ultimo_heartbeat = 0.0
    while True:
        try:
            LOG.info("Conectando con Arduino en %s", puerto)
            with serial.Serial(puerto, velocidad, timeout=1) as dispositivo:
                time.sleep(2)  # El Uno reinicia al abrir el puerto serie.
                while True:
                    if time.monotonic() - ultimo_heartbeat >= 30:
                        ultimo_heartbeat = time.monotonic()
                        try:
                            hb = requests.post(
                                endpoint.rsplit("/", 1)[0] + "/heartbeat",
                                params={"codigo_dispositivo": codigo_dispositivo},
                                headers={"X-Reader-Token": token},
                                timeout=5,
                            )
                            hb.raise_for_status()
                        except requests.RequestException as error:
                            LOG.warning("No se pudo actualizar el contacto del lector (%s)", type(error).__name__)
                    linea = dispositivo.readline().decode("ascii", errors="ignore")
                    uid = parse_uid_line(linea)
                    if uid is None:
                        if linea.strip():
                            LOG.warning("Línea serial inválida descartada")
                        continue
                    ahora = time.monotonic()
                    if uid == ultimo_uid and ahora - ultima_envio < cooldown:
                        continue
                    try:
                        respuesta = requests.post(
                            endpoint,
                            json={"uid": uid, "codigo_dispositivo": codigo_dispositivo},
                            headers={"X-Reader-Token": token},
                            timeout=5,
                        )
                        respuesta.raise_for_status()
                        LOG.info("Lectura procesada por API (HTTP %s)", respuesta.status_code)
                    except requests.RequestException as error:
                        # No registrar URL, payload ni encabezados; no contienen credenciales.
                        LOG.error("No se pudo comunicar con FastAPI (%s)", type(error).__name__)
                        continue
                    ultimo_uid, ultima_envio = uid, ahora
        except (serial.SerialException, OSError) as error:
            LOG.warning("Arduino desconectado (%s); reintento en 3 s", type(error).__name__)
            time.sleep(3)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=os.getenv("EDUTRACK_SERIAL_PORT"))
    parser.add_argument("--baud", type=int, default=int(os.getenv("EDUTRACK_SERIAL_BAUD", "115200")))
    parser.add_argument("--endpoint", default=os.getenv("EDUTRACK_RFID_ENDPOINT", "http://localhost:8000/rfid/lecturas"))
    parser.add_argument("--device-code", default=os.getenv("EDUTRACK_DEVICE_CODE"))
    token = os.getenv("EDUTRACK_RFID_TOKEN", "")
    parser.add_argument("--cooldown", type=float, default=2.0, help="Segundos para deduplicar UID consecutivo")
    args = parser.parse_args()
    if not args.device_code or not token:
        parser.error("Configura EDUTRACK_DEVICE_CODE y EDUTRACK_RFID_TOKEN en el entorno.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        ejecutar(elegir_puerto(args.port), args.baud, args.endpoint, args.cooldown, args.device_code, token)
    except RuntimeError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
