"""Receptor serial Arduino/RC522, cola SQLite y sincronización HTTP."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import time
from datetime import datetime

import requests

from queue_store import ReadingQueue
from serial_reader import SerialUIDReader
from synchronizer import Synchronizer

LOG = logging.getLogger("edutrack-reader")
DETENER = False


def _solicitar_detencion(_signal_number, _frame):
    global DETENER
    DETENER = True


def ejecutar(endpoint: str, device_code: str, token: str, queue_path: str,
             sync_interval: float, batch_size: int, serial_port: str,
             baud_rate: int, dedupe_seconds: float) -> None:
    queue = ReadingQueue(queue_path)
    synchronizer = Synchronizer(queue, endpoint, token, batch_size)
    reader = SerialUIDReader(serial_port, baud_rate)
    ultima_lectura: tuple[str, float] | None = None
    next_sync = 0.0
    next_heartbeat = 0.0
    LOG.info("Receptor serial listo en %s a %d baudios; cola: %s", serial_port, baud_rate, queue_path)
    try:
        while not DETENER:
            now = time.monotonic()
            uid = reader.read_uid()
            if uid:
                instante = time.monotonic()
                if ultima_lectura and uid == ultima_lectura[0] and instante - ultima_lectura[1] < dedupe_seconds:
                    LOG.info("Lectura repetida de la misma tarjeta ignorada")
                else:
                    row_id = queue.enqueue(uid, device_code, datetime.now().astimezone().isoformat())
                    ultima_lectura = (uid, instante)
                    LOG.info("Lectura %d encolada; %d pendientes", row_id, queue.count())

            now = time.monotonic()
            if now >= next_sync:
                synchronizer.synchronize()
                next_sync = now + sync_interval
            if now >= next_heartbeat:
                try:
                    response = requests.post(
                        endpoint.rsplit("/", 1)[0] + "/heartbeat",
                        params={"codigo_dispositivo": device_code},
                        headers={"X-Reader-Token": token},
                        timeout=5,
                    )
                    response.raise_for_status()
                except requests.RequestException as error:
                    LOG.warning("No se pudo actualizar el contacto del lector (%s)", type(error).__name__)
                next_heartbeat = now + 30
            time.sleep(0.05)
    finally:
        reader.close()
        LOG.info("Lector detenido; %d lecturas permanecen en cola", queue.count())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=os.getenv("EDUTRACK_RFID_ENDPOINT", "http://localhost:8000/rfid/lecturas"))
    parser.add_argument("--device-code", default=os.getenv("EDUTRACK_DEVICE_CODE"))
    parser.add_argument("--queue", default=os.getenv("EDUTRACK_RFID_QUEUE", "./data/readings.sqlite3"))
    parser.add_argument("--sync-interval", type=float, default=float(os.getenv("EDUTRACK_SYNC_INTERVAL", "10")))
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("EDUTRACK_BATCH_SIZE", "50")))
    parser.add_argument("--serial-port", default=os.getenv("EDUTRACK_SERIAL_PORT", ""))
    parser.add_argument("--baud-rate", type=int, default=int(os.getenv("EDUTRACK_SERIAL_BAUD", "9600")))
    parser.add_argument("--dedupe-seconds", type=float, default=float(os.getenv("EDUTRACK_DEDUPE_SECONDS", "2")))
    args = parser.parse_args()
    token = os.getenv("EDUTRACK_RFID_TOKEN", "")
    if not args.device_code or not token:
        parser.error("Configura EDUTRACK_DEVICE_CODE y EDUTRACK_RFID_TOKEN en el entorno.")
    if not args.serial_port:
        parser.error("Indica --serial-port o configura EDUTRACK_SERIAL_PORT.")
    if args.sync_interval <= 0 or args.batch_size <= 0 or args.baud_rate <= 0 or args.dedupe_seconds < 0:
        parser.error("Intervalos, tamaño de lote y velocidad deben ser válidos.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGINT, _solicitar_detencion)
    signal.signal(signal.SIGTERM, _solicitar_detencion)
    ejecutar(args.endpoint, args.device_code, token, args.queue, args.sync_interval,
             args.batch_size, args.serial_port, args.baud_rate, args.dedupe_seconds)


if __name__ == "__main__":
    main()
