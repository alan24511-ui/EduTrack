"""Autenticación HTTP del endpoint de ingesta, sin PostgreSQL ni secretos reales."""

from fastapi.testclient import TestClient

from app.main import app
from app.routes import rfid


class CursorFalso:
    def __init__(self):
        self.resultado = None

    def __enter__(self): return self
    def __exit__(self, *_args): return False

    def execute(self, sql, params=()):
        if 'SELECT "Id_Dispositivo", "Estado"' in sql:
            self.resultado = (7, "activo")
        elif 'SELECT c."id_Tarjeta"' in sql:
            self.resultado = None
        else:
            self.resultado = None

    def fetchone(self): return self.resultado


class ConexionFalsa:
    def __enter__(self): return self
    def __exit__(self, *_args): return False
    def cursor(self): return CursorFalso()


def test_ingesta_exige_token_configurado_y_acepta_el_valido(monkeypatch):
    monkeypatch.setattr(rfid, "obtener_settings", lambda: type("Settings", (), {
        "ingesta_token": "secreto-de-prueba", "rfid_debounce_seconds": 5,
    })())
    monkeypatch.setattr(rfid, "obtener_conexion", ConexionFalsa)
    client = TestClient(app)
    body = {"uid": "04123456", "codigo_dispositivo": "lector-prueba"}

    assert client.post("/rfid/lecturas", json=body).status_code == 401
    assert client.post("/rfid/lecturas", json=body,
                       headers={"X-Ingesta-Token": "incorrecto"}).status_code == 401
    response = client.post("/rfid/lecturas", json=body,
                           headers={"X-Ingesta-Token": "secreto-de-prueba"})
    assert response.status_code == 200
    assert response.json()["resultado"] == "TARJETA_NO_REGISTRADA"


def test_ingesta_sin_secreto_configurado_falla_cerrado(monkeypatch):
    monkeypatch.setattr(rfid, "obtener_settings", lambda: type("Settings", (), {
        "ingesta_token": "", "rfid_debounce_seconds": 5,
    })())
    response = TestClient(app).post(
        "/rfid/lecturas", json={"uid": "04123456", "codigo_dispositivo": "lector-prueba"},
        headers={"X-Ingesta-Token": "cualquier-valor"},
    )
    assert response.status_code == 503
