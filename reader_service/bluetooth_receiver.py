"""Lee UIDs del HC-05 por RFCOMM y los entrega al endpoint RFID de EduTrack."""

from __future__ import annotations

import argparse
import logging
import os
import re
import time

import requests
import serial
from serial import SerialException

UID_RE = re.compile(r"^[0-9A-Fa-f]{8}(?:[0-9A-Fa-f]{6})?(?:[0-9A-Fa-f]{6})?$")
LINE_RE = re.compile(r"^UID:([0-9A-Fa-f]{8}(?:[0-9A-Fa-f]{6})?(?:[0-9A-Fa-f]{6})?)$", re.IGNORECASE)
LOG = logging.getLogger("edutrack.bluetooth")


def cargar_configuracion_local() -> None:
    """Carga variables de reader_service/.env sin reemplazar las del entorno."""
    config_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(config_path, encoding="utf-8") as config_file:
            for raw_line in config_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    except FileNotFoundError:
        pass


def extraer_uid(linea: str) -> str | None:
    """Valida mensajes UID: de 4, 7 o 10 bytes y normaliza a mayúsculas."""
    match = LINE_RE.fullmatch(linea.strip())
    if not match:
        return None
    uid = match.group(1).upper()
    return uid if UID_RE.fullmatch(uid) else None


class BluetoothReceiver:
    def __init__(self, port: str, baud: int, api_url: str, device_code: str,
                 token: str, reconnect_seconds: float = 3, duplicate_seconds: float = 2,
                 heartbeat_seconds: float = 15):
        self.port = port
        self.baud = baud
        self.endpoint = api_url.rstrip("/") + "/rfid/lecturas"
        self.capture_endpoint = api_url.rstrip("/") + "/rfid/reader/capture"
        self.device_code = device_code
        self.token = token
        self.reconnect_seconds = reconnect_seconds
        self.duplicate_seconds = duplicate_seconds
        self.heartbeat_endpoint = api_url.rstrip("/") + "/rfid/heartbeat"
        self.heartbeat_seconds = heartbeat_seconds
        self._last_uid: str | None = None
        self._last_sent_at = 0.0

    def reportar_estado(self, estado: str = "conectado",
                        session: requests.Session | None = None) -> bool:
        if estado != "conectado":
            return False
        client = session or requests
        try:
            response = client.post(
                self.heartbeat_endpoint,
                params={"codigo_dispositivo": self.device_code, "tipo": "bluetooth"},
                headers={"X-Reader-Token": self.token},
                timeout=5,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            LOG.error("No se pudo informar el estado Bluetooth a FastAPI: %s", exc)
            return False

    def procesar_linea(self, linea: str, session: requests.Session | None = None) -> bool:
        uid = extraer_uid(linea)
        if uid is None:
            LOG.warning("Mensaje Bluetooth inválido ignorado: %r", linea.strip())
            return False
        now = time.monotonic()
        client = session or requests
        try:
            capture_response = client.post(
                self.capture_endpoint,
                json={"uid": uid, "codigo_dispositivo": self.device_code},
                headers={"X-Reader-Token": self.token},
                timeout=5,
            )
            capture_response.raise_for_status()
            if capture_response.json().get("capturada"):
                self._last_uid, self._last_sent_at = uid, now
                LOG.info("UID %s reservado para la asociación administrativa", uid)
                return True
        except requests.RequestException as exc:
            LOG.error("No se pudo comprobar la captura administrativa para UID %s: %s", uid, exc)
            return False
        if uid == self._last_uid and now - self._last_sent_at < self.duplicate_seconds:
            LOG.info("UID duplicado reciente ignorado: %s", uid)
            return False
        try:
            response = client.post(
                self.endpoint,
                json={"uid": uid, "codigo_dispositivo": self.device_code},
                headers={"X-Reader-Token": self.token},
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
        except requests.RequestException as exc:
            LOG.error("No se pudo enviar UID %s a FastAPI: %s", uid, exc)
            return False
        self._last_uid, self._last_sent_at = uid, now
        LOG.info("UID %s: %s — %s", uid, result.get("resultado", "procesado"), result.get("mensaje", ""))
        return True

    def run(self) -> None:
        LOG.info("Receptor EduTrack listo: %s a %s baudios; API %s", self.port, self.baud, self.endpoint)
        while True:
            try:
                with serial.Serial(self.port, self.baud, timeout=1) as connection:
                    LOG.info("Bluetooth conectado en %s", self.port)
                    next_heartbeat = 0.0
                    while True:
                        if time.monotonic() >= next_heartbeat:
                            if not self.reportar_estado("conectado"):
                                LOG.warning("FastAPI no confirmó el heartbeat del receptor Bluetooth")
                            next_heartbeat = time.monotonic() + self.heartbeat_seconds
                        raw = connection.readline()
                        if raw:
                            self.procesar_linea(raw.decode("ascii", errors="replace"))
            except (SerialException, OSError) as exc:
                LOG.error("Sin conexión Bluetooth en %s: %s. Reintentando en %.1f s", self.port, exc, self.reconnect_seconds)
                time.sleep(self.reconnect_seconds)


def main() -> None:
    cargar_configuracion_local()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=os.getenv("EDUTRACK_BT_PORT", "/dev/rfcomm0"))
    parser.add_argument("--baud", type=int, default=int(os.getenv("EDUTRACK_BT_BAUD", "9600")))
    parser.add_argument("--api-url", default=os.getenv("EDUTRACK_API_URL", "http://localhost:8000"))
    parser.add_argument("--device-code", default=os.getenv("EDUTRACK_DEVICE_CODE", ""))
    parser.add_argument("--token", default=os.getenv("EDUTRACK_RFID_TOKEN", ""))
    parser.add_argument("--reconnect-seconds", type=float, default=3)
    parser.add_argument("--heartbeat-seconds", type=float, default=15)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not args.device_code or not args.token:
        parser.error("Configura EDUTRACK_DEVICE_CODE y EDUTRACK_RFID_TOKEN (o los argumentos equivalentes).")
    if not 0 < args.heartbeat_seconds < 45 or args.reconnect_seconds <= 0:
        parser.error("El heartbeat debe ser mayor a cero y menor a 45 segundos; la reconexión debe ser mayor a cero.")
    BluetoothReceiver(args.port, args.baud, args.api_url, args.device_code, args.token,
                      args.reconnect_seconds, heartbeat_seconds=args.heartbeat_seconds).run()


if __name__ == "__main__":
    main()
