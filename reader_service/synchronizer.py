"""Entrega por ciclos los registros de la cola usando el contrato RFID actual."""

from __future__ import annotations

import logging

import requests

from queue_store import ReadingQueue

LOG = logging.getLogger("edutrack-reader")


class Synchronizer:
    def __init__(self, queue: ReadingQueue, endpoint: str, token: str, batch_size: int = 50):
        self.queue = queue
        self.endpoint = endpoint
        self.headers = {"X-Reader-Token": token}
        self.batch_size = batch_size

    def synchronize(self) -> int:
        """Procesa hasta un lote; cada fila usa POST /rfid/lecturas existente."""
        delivered = 0
        for reading_id, uid, device_code, _captured_at in self.queue.pending(self.batch_size):
            try:
                response = requests.post(
                    self.endpoint,
                    json={"uid": uid, "codigo_dispositivo": device_code},
                    headers=self.headers,
                    timeout=8,
                )
                response.raise_for_status()
            except requests.RequestException as error:
                # Conserva esta y todas las siguientes filas para el siguiente ciclo.
                LOG.warning("Sincronización pausada; %s lecturas siguen pendientes (%s)", self.queue.count(), type(error).__name__)
                break
            self.queue.acknowledge(reading_id)
            delivered += 1
        if delivered:
            LOG.info("Lote sincronizado: %d lecturas; %d pendientes", delivered, self.queue.count())
        return delivered
