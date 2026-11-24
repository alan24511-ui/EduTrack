from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from threading import Lock
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks

from app.routes import rfid
from app.schemas import LecturaRFIDEntrada

ZONA = ZoneInfo("America/Mexico_City")


class BaseDatosFalsa:
    """Modelo transaccional pequeño para probar concurrencia sin Supabase."""
    def __init__(self):
        self.ahora = datetime(2026, 11, 18, 8, 0, tzinfo=ZONA)
        self.dispositivos = {"lector-prueba": (7, "activo")}
        self.estudiantes = {3: ("Ana", "M1", "A"), 4: ("Luis", "M2", "B")}
        self.tarjetas = {
            "04123456": (9, 3, None, None),
            "04123457": (10, 4, None, None),
            "04123458": (11, 3, None, date(2020, 1, 2)),
        }
        self.asistencias = {}
        self.accesos = []
        self.bloqueos = {3: Lock(), 4: Lock()}
        self.siguiente_id = 40


class Reloj:
    def __init__(self, db): self.db = db
    def now(self, zona): return self.db.ahora.astimezone(zona)


class CursorFalso:
    def __init__(self, db):
        self.db = db
        self.resultado = None
        self.bloqueo = None

    def __enter__(self): return self
    def __exit__(self, *_args): return False

    def execute(self, sql, params=()):
        self.resultado = None
        if 'SELECT "Id_Dispositivo", "Estado"' in sql:
            self.resultado = self.db.dispositivos.get(params[0])
        elif 'SELECT c."id_Tarjeta"' in sql:
            tarjeta = self.db.tarjetas.get(params[0])
            if tarjeta:
                tarjeta_id, estudiante_id, inicio, termino = tarjeta
                nombre, matricula, grupo = self.db.estudiantes[estudiante_id]
                self.resultado = (tarjeta_id, estudiante_id, inicio, termino, nombre, matricula, grupo)
        elif 'SELECT "Id_Estudiante" FROM "Estudiantes"' in sql:
            estudiante_id = params[0]
            self.bloqueo = self.db.bloqueos[estudiante_id]
            self.bloqueo.acquire()
            self.resultado = (estudiante_id,) if estudiante_id in self.db.estudiantes else None
        elif 'SELECT 1 FROM "Registros_accesos"' in sql:
            tarjeta_id, ahora, segundos, entrada, salida = params
            limite = ahora - timedelta(seconds=segundos)
            self.resultado = next((
                (1,) for fila in reversed(self.db.accesos)
                if fila[3] == tarjeta_id and fila[0] >= limite and fila[4] in (entrada, salida)
            ), None)
        elif 'SELECT "id_asistencia"' in sql:
            estudiante_id, fecha = params
            registro = self.db.asistencias.get((estudiante_id, fecha))
            if registro:
                self.resultado = (registro[0], registro[1], registro[2])
        elif 'INSERT INTO "Asistencia"' in sql:
            estado, fecha, entrada, estudiante_id = params
            self.db.siguiente_id += 1
            self.db.asistencias[(estudiante_id, fecha)] = [self.db.siguiente_id, entrada, None, True, estado]
            self.resultado = (self.db.siguiente_id,)
        elif 'UPDATE "Asistencia" SET "Hora_Salida"' in sql:
            hora_salida, asistencia_id = params
            for registro in self.db.asistencias.values():
                if registro[0] == asistencia_id: registro[2] = hora_salida
        elif 'UPDATE "Asistencia" SET "Asistencia"' in sql:
            estado, entrada, asistencia_id = params
            for registro in self.db.asistencias.values():
                if registro[0] == asistencia_id:
                    registro[1], registro[3], registro[4] = entrada, True, estado
        elif 'INSERT INTO "Registros_accesos"' in sql:
            self.db.accesos.append(params)
        elif 'SELECT "Hora_de_entrada"' in sql:
            self.resultado = None

    def fetchone(self): return self.resultado

    def liberar(self):
        if self.bloqueo:
            self.bloqueo.release()
            self.bloqueo = None


class ConexionFalsa:
    def __init__(self, db):
        self.db = db
        self.cursor_actual = None
    def __enter__(self): return self
    def __exit__(self, *_args):
        if self.cursor_actual: self.cursor_actual.liberar()
        return False
    def cursor(self):
        self.cursor_actual = CursorFalso(self.db)
        return self.cursor_actual


def preparar(monkeypatch, db):
    monkeypatch.setattr(rfid, "_validar_lector", lambda _token: None)
    monkeypatch.setattr(rfid, "obtener_conexion", lambda: ConexionFalsa(db))
    monkeypatch.setattr(rfid, "obtener_settings", lambda: SimpleNamespace(rfid_debounce_seconds=5))
    monkeypatch.setattr(rfid, "datetime", Reloj(db))


def leer(uid):
    return rfid.procesar_lectura(
        LecturaRFIDEntrada(uid=uid, codigo_dispositivo="lector-prueba"),
        BackgroundTasks(), "token-prueba",
    )


def test_primera_lectura_registra_entrada(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    r = leer("04123456")
    assert r["resultado"] == "ENTRADA_REGISTRADA"
    assert r["evento"] == "ENTRADA" and r["estudiante"] == "Ana"
    assert len(db.asistencias) == 1


def test_segunda_lectura_despues_del_debounce_registra_salida(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    leer("04123456"); db.ahora += timedelta(seconds=6)
    r = leer("04123456")
    assert r["resultado"] == "SALIDA_REGISTRADA"
    assert next(iter(db.asistencias.values()))[2] is not None
    assert len(db.asistencias) == 1


def test_lectura_inmediata_no_modifica_asistencia(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    leer("04123456"); previo = [row.copy() for row in db.asistencias.values()]
    r = leer("04123456")
    assert r["resultado"] == "LECTURA_DUPLICADA"
    assert list(db.asistencias.values()) == previo


def test_tercera_lectura_informa_asistencia_completa(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    leer("04123456"); db.ahora += timedelta(seconds=6); leer("04123456")
    previo = [row.copy() for row in db.asistencias.values()]
    db.ahora += timedelta(seconds=6); r = leer("04123456")
    assert r["resultado"] == "ASISTENCIA_COMPLETA"
    assert list(db.asistencias.values()) == previo


def test_tarjeta_no_registrada_se_rechaza(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    assert leer("04123499")["resultado"] == "TARJETA_NO_REGISTRADA"
    assert not db.asistencias


def test_tarjeta_fuera_de_vigencia_se_rechaza_como_desactivada(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    assert leer("04123458")["resultado"] == "TARJETA_DESACTIVADA"
    assert not db.asistencias


def test_alumnos_distintos_tienen_asistencias_independientes(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    assert leer("04123456")["resultado"] == "ENTRADA_REGISTRADA"
    assert leer("04123457")["resultado"] == "ENTRADA_REGISTRADA"
    assert len(db.asistencias) == 2


def test_dos_lecturas_concurrentes_no_convierten_entrada_en_salida(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        respuestas = list(pool.map(lambda _: leer("04123456"), range(2)))
    assert sorted(r["resultado"] for r in respuestas) == ["ENTRADA_REGISTRADA", "LECTURA_DUPLICADA"]
    assert len(db.asistencias) == 1
    assert next(iter(db.asistencias.values()))[2] is None


def test_cambio_de_fecha_local_crea_asistencia_del_nuevo_dia(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    leer("04123456"); db.ahora += timedelta(days=1)
    r = leer("04123456")
    assert r["resultado"] == "ENTRADA_REGISTRADA"
    assert len(db.asistencias) == 2


def test_reinicio_simulado_conserva_asistencia_persistida(monkeypatch):
    db = BaseDatosFalsa(); preparar(monkeypatch, db)
    leer("04123456"); db.ahora += timedelta(seconds=6)
    # Simula un proceso nuevo reutilizando solo el almacenamiento persistente.
    preparar(monkeypatch, db)
    r = leer("04123456")
    assert r["resultado"] == "SALIDA_REGISTRADA"
    assert len(db.asistencias) == 1
    assert next(iter(db.asistencias.values()))[2] is not None
