"""Lector persistente Arduino/RC522 para captura administrativa bajo demanda."""

from __future__ import annotations

import logging
import fcntl
import hashlib
import re
import threading
import time
import uuid
from contextlib import contextmanager

from serial import Serial, SerialException
from serial.tools import list_ports

LOG = logging.getLogger(__name__)
UID_RE = re.compile(r"^[0-9A-Fa-f]{8}(?:[0-9A-Fa-f]{6})?(?:[0-9A-Fa-f]{6})?$")


class RFIDReader:
    def __init__(self, baud: int = 9600, preferred_port: str = ""):
        self.baud = baud
        self.preferred_port = preferred_port
        self._lock = threading.RLock()
        self._serial: Serial | None = None
        self._port_lock = None
        self._port: str | None = None
        self._reader_ok = False
        self._error: str | None = None
        self._capture: dict | None = None
        self._last_ping = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="edutrack-rfid-serial", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        with self._lock:
            self._close_locked("Backend detenido.")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def status(self):
        with self._lock:
            return {"conectado": bool(self._serial and self._serial.is_open and self._reader_ok),
                    "puerto": self._port, "lectorListo": self._reader_ok,
                    "capturando": bool(self._capture and not self._capture["done"].is_set()),
                    "error": self._error}

    def begin_capture(self, capture_id: str | None = None) -> str:
        with self._lock:
            if not (self._serial and self._serial.is_open and self._reader_ok):
                raise RuntimeError(self._error or "El lector RFID no está conectado o no está inicializado.")
            if self._capture and not self._capture["done"].is_set():
                raise RuntimeError("Ya hay una lectura RFID en curso.")
            capture_id = capture_id or str(uuid.uuid4())
            capture = {"id": capture_id, "done": threading.Event(), "uid": None, "cancelled": False, "error": None}
            self._capture = capture
            try:
                self._serial.write(b"READ\n")
            except SerialException as error:
                self._close_locked("Arduino desconectado; buscando el lector nuevamente.")
                raise RuntimeError("Se perdió la comunicación USB con Arduino.") from error
            return capture_id

    def wait_capture(self, capture_id: str, timeout: float = 60):
        with self._lock:
            capture = self._capture
            if not capture or capture["id"] != capture_id:
                raise RuntimeError("La solicitud de lectura ya no está activa.")
        if not capture["done"].wait(timeout):
            self.cancel_capture(capture_id)
            raise TimeoutError("No se recibió una tarjeta en 60 segundos.")
        with self._lock:
            if capture["cancelled"]:
                raise InterruptedError("Lectura cancelada.")
            if capture["error"]:
                raise RuntimeError(capture["error"])
            return capture["uid"]

    def cancel_capture(self, capture_id: str | None = None):
        with self._lock:
            capture = self._capture
            if not capture or (capture_id and capture["id"] != capture_id):
                return False
            if capture["done"].is_set():
                return False
            capture["cancelled"] = True
            capture["done"].set()
            if self._serial and self._serial.is_open:
                try:
                    self._serial.write(b"CANCEL\n")
                except SerialException:
                    pass
            return True

    def is_cancelled(self, capture_id: str) -> bool:
        with self._lock:
            return not self._capture or self._capture["id"] != capture_id or self._capture["cancelled"]

    @contextmanager
    def proteger_captura(self, capture_id: str):
        """Evita cancelar/reemplazar una captura mientras su UID se persiste."""
        with self._lock:
            capture = self._capture
            if not capture or capture["id"] != capture_id or capture["cancelled"] or not capture["done"].is_set():
                raise InterruptedError("La solicitud de lectura ya no está activa.")
            yield

    def _close_locked(self, reason: str):
        if self._capture and not self._capture["done"].is_set():
            self._capture["error"] = reason
            self._capture["done"].set()
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        if self._port_lock:
            try:
                fcntl.flock(self._port_lock.fileno(), fcntl.LOCK_UN)
                self._port_lock.close()
            except OSError:
                pass
        self._port_lock = None
        self._port = None
        self._reader_ok = False
        self._error = reason

    def _candidate_ports(self):
        ports = list(list_ports.comports())
        if self.preferred_port:
            ports.sort(key=lambda p: p.device != self.preferred_port)
        else:
            ports.sort(key=lambda p: not any(s in f"{p.description} {p.manufacturer}".lower()
                                             for s in ("arduino", "ch340", "ch341", "usb serial", "usb-serial", "ftdi")))
        return ports

    def _connect(self):
        for port in self._candidate_ports():
            if self._stop.is_set():
                return
            device = port.device
            lock_path = "/tmp/edutrack-rfid-" + hashlib.sha256(device.encode()).hexdigest()[:16] + ".lock"
            try:
                port_lock = open(lock_path, "w")
                try:
                    fcntl.flock(port_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    port_lock.close()
                    continue
                candidate = Serial(device, self.baud, timeout=0.15, write_timeout=1)
                time.sleep(1.8)  # El Uno reinicia al abrir el puerto USB.
                candidate.reset_input_buffer()
                candidate.write(b"PING\n")
                deadline = time.monotonic() + 2
                response = ""
                while time.monotonic() < deadline:
                    line = candidate.readline().decode("ascii", errors="ignore").strip()
                    if line.startswith("READY:EDUTRACK_RFID:1:"):
                        response = line
                        break
                if not response:
                    candidate.close()
                    fcntl.flock(port_lock.fileno(), fcntl.LOCK_UN)
                    port_lock.close()
                    continue
                with self._lock:
                    self._serial, self._port = candidate, device
                    self._port_lock = port_lock
                    self._reader_ok = response.endswith(":OK")
                    self._error = None if self._reader_ok else "El RC522 no respondió al firmware (" + response + ")."
                LOG.info("Lector EduTrack detectado en %s: %s", device, response)
                return
            except (SerialException, OSError) as exc:
                try:
                    candidate.close()
                except (NameError, SerialException, OSError):
                    pass
                try:
                    fcntl.flock(port_lock.fileno(), fcntl.LOCK_UN)
                    port_lock.close()
                except (NameError, OSError):
                    pass
                with self._lock:
                    self._error = f"No se pudo abrir {device}: {exc}"

    def _run(self):
        while not self._stop.is_set():
            with self._lock:
                ser = self._serial
            if ser is None:
                self._connect()
                if self._serial is None:
                    self._stop.wait(2)
                    continue
                continue
            try:
                with self._lock:
                    if not self._reader_ok and time.monotonic() - self._last_ping > 5:
                        ser.write(b"PING\n")
                        self._last_ping = time.monotonic()
                line = ser.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    continue
                if line == "ERROR:RC522_INIT":
                    with self._lock:
                        self._reader_ok = False
                        self._error = "El firmware informa que el RC522 no está inicializado."
                elif line.startswith("UID:"):
                    uid = line.partition(":")[2].strip().upper()
                    if UID_RE.fullmatch(uid):
                        with self._lock:
                            capture = self._capture
                            if capture and not capture["done"].is_set():
                                capture["uid"] = uid
                                capture["done"].set()
                elif line.startswith("READY:EDUTRACK_RFID:1:"):
                    with self._lock:
                        self._reader_ok = line.endswith(":OK")
                        self._error = None if self._reader_ok else "RC522 no inicializado."
            except (SerialException, OSError) as exc:
                LOG.warning("Conexión RFID perdida: %s", exc)
                with self._lock:
                    self._close_locked("Arduino desconectado; buscando el lector nuevamente.")


lector_rfid: RFIDReader | None = None


def configurar_lector(baud: int, port: str = "") -> RFIDReader:
    global lector_rfid
    if lector_rfid is None:
        lector_rfid = RFIDReader(baud, port)
    return lector_rfid
