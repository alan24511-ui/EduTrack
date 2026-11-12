"""Acceso al RC522 conectado directamente al bus SPI de Raspberry Pi."""

from __future__ import annotations

import logging
import time

LOG = logging.getLogger("edutrack-reader")


def canonical_uid(uid: list[int] | tuple[int, ...]) -> str:
    """Convierte los bytes devueltos por anticoll a hexadecimal, conservando ceros."""
    if len(uid) not in (4, 7, 10):
        raise ValueError("El RC522 devolvió un UID de longitud no soportada")
    return "".join(f"{byte:02X}" for byte in uid)


class RC522Reader:
    def __init__(self):
        try:
            from pirc522 import RFID
        except ImportError as error:
            raise RuntimeError("Falta la dependencia pi-rc522 (módulo pirc522)") from error
        # pirc522 usa numeración física BOARD por defecto: pin 15 = BCM GPIO22.
        # El IRQ no está cableado y CE0 lo controla el kernel SPI (/dev/spidev0.0).
        self._reader = RFID(pin_rst=15, pin_irq=None)
        self._latched = False
        self._missing_since: float | None = None

    def poll_uid(self) -> str | None:
        """Devuelve un UID una vez por colocación; None si no hay tarjeta nueva."""
        uid = self._reader.read_id()
        if uid is None:
            if self._latched:
                if self._missing_since is None:
                    self._missing_since = time.monotonic()
                elif time.monotonic() - self._missing_since >= 0.5:
                    self._latched = False
                    self._missing_since = None
            return None
        if self._latched:
            self._missing_since = None
            return None
        value = canonical_uid(uid)
        self._latched = True
        self._missing_since = None
        LOG.info("Tarjeta nueva detectada")
        return value

    def close(self) -> None:
        cleanup = getattr(self._reader, "cleanup", None)
        if cleanup:
            cleanup()
