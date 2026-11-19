from fastapi import BackgroundTasks, HTTPException

from app.routes import rfid
from app.schemas import LecturaRFIDEntrada


class CursorFalso:
    def __init__(self, modo):
        self.modo = modo
        self.resultado = None
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, _params=()):
        self.resultado = None
        if 'SELECT "Id_Dispositivo", "Estado"' in sql:
            self.resultado = (7, "inactivo" if self.modo == "dispositivo_inactivo" else "activo")
        elif 'SELECT c."id_Tarjeta"' in sql:
            if self.modo == "desconocida":
                self.resultado = None
            elif self.modo == "vencida":
                from datetime import date
                self.resultado = (9, 3, date(2020, 1, 1), date(2020, 1, 2), "Ana", "M1", "A")
            else:
                self.resultado = (9, 3, None, None, "Ana", "M1", "A")
        elif 'SELECT 1 FROM "Registros_accesos"' in sql:
            self.resultado = None
        elif 'SELECT "Id_Estudiante" FROM "Estudiantes"' in sql:
            self.resultado = (3,)
        elif 'SELECT "id_asistencia"' in sql:
            self.resultado = None
        elif 'RETURNING "id_asistencia"' in sql:
            self.resultado = (42,)
        elif 'SELECT "Hora_de_entrada"' in sql:
            self.resultado = None

    def fetchone(self):
        return self.resultado


class ConexionFalsa:
    def __init__(self, modo):
        self.modo = modo

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return CursorFalso(self.modo)


def ejecutar(monkeypatch, modo, uid):
    monkeypatch.setattr(rfid, "_validar_lector", lambda _token: None)
    monkeypatch.setattr(rfid, "obtener_conexion", lambda: ConexionFalsa(modo))
    datos = LecturaRFIDEntrada(uid=uid, codigo_dispositivo="lector-prueba")
    return rfid.procesar_lectura(datos, BackgroundTasks(), "token-prueba")


def test_tarjeta_registrada_registra_entrada(monkeypatch):
    result = ejecutar(monkeypatch, "registrada", "04123456")
    assert result["resultado"] == "registrada"
    assert result["evento"] == "entrada"
    assert result["estudiante"] == "Ana"


def test_rechaza_tarjeta_desconocida_y_vencida(monkeypatch):
    assert ejecutar(monkeypatch, "desconocida", "04123457")["resultado"] == "tarjeta_desconocida"
    assert ejecutar(monkeypatch, "vencida", "04123458")["resultado"] == "tarjeta_vencida"


def test_rechaza_dispositivo_inactivo(monkeypatch):
    try:
        ejecutar(monkeypatch, "dispositivo_inactivo", "04123459")
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError("Se esperaba rechazar el dispositivo inactivo")


def test_ignora_repeticion_de_misma_lectura(monkeypatch):
    uid = "04123460"
    assert ejecutar(monkeypatch, "registrada", uid)["resultado"] == "registrada"
    assert ejecutar(monkeypatch, "registrada", uid)["resultado"] == "lectura_duplicada"
