"""Recepción y validación del protocolo serial del firmware Arduino."""

from __future__ import annotations

import logging
import re
import time

import serial

LOG = logging.getLogger("edutrack-reader")
UID_LINE = re.compile(r"^UID:\s*([0-9A-Fa-f]+)\s*$")


class SerialUIDReader:
    def __init__(self, port: str, baud_rate: int = 9600):
        self.port = port
        self.baud_rate = baud_rate
        self.connection: serial.Serial | None = None
        self.retry_at = 0.0

    def _connect(self) -> bool:
        if self.connection and self.connection.is_open:
            return True
        if time.monotonic() < self.retry_at:
            return False
        try:
            self.connection = serial.Serial(self.port, self.baud_rate, timeout=0.5)
            # Algunas placas se reinician al abrir el puerto USB.
            time.sleep(2)
            self.connection.reset_input_buffer()
            LOG.info("Arduino conectado por serial")
            return True
        except serial.SerialException as error:
            LOG.warning("No se pudo abrir el puerto serial %s (%s)", self.port, type(error).__name__)
            self.connection = None
            self.retry_at = time.monotonic() + 3
            return False

    def read_uid(self) -> str | None:
        if not self._connect():
            return None
        try:
            line = self.connection.readline().decode("ascii", errors="ignore").strip()
        except (serial.SerialException, OSError) as error:
            LOG.warning("Se perdió la conexión serial (%s); se intentará reconectar", type(error).__name__)
            self.close()
            self.retry_at = time.monotonic() + 3
            return None
        if not line:
            return None
        match = UID_LINE.fullmatch(line)
        if not match:
            LOG.debug("Línea serial ignorada: formato no reconocido")
            return None
        uid = match.group(1).upper()
        if len(uid) not in (8, 14, 20):
            LOG.warning("UID serial ignorado por longitud no válida")
            return None
        return uid

    def close(self) -> None:
        if self.connection:
            try:
                self.connection.close()
            finally:
                self.connection = None
