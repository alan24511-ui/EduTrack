from unittest.mock import patch

from app.rfid_reader import RFIDReader, extraer_uid


def test_extrae_uid_hexadecimal_en_mayusculas():
    assert extraer_uid("EDUTRACK_RFID:UID:04a1b2c3") == "04A1B2C3"
    assert extraer_uid("EDUTRACK_RFID:UID:04112233445566") == "04112233445566"
    assert extraer_uid("EDUTRACK_RFID:UID:04112233445566778899") == "04112233445566778899"


def test_rechaza_diagnosticos_y_uids_invalidos():
    assert extraer_uid("EDUTRACK_RFID:INICIADO") is None
    assert extraer_uid("EDUTRACK_RFID:ERROR:RC522_INIT") is None
    assert extraer_uid("UID:04A1B2C3") is None
    assert extraer_uid("EDUTRACK_RFID:UID:1234") is None
    assert extraer_uid("EDUTRACK_RFID:UID:04A1B2C3ZZ") is None


def test_reconecta_al_desconectarse_el_serial():
    class Puerto:
        device = "/dev/ttyACM0"
        description = "Arduino Uno"
        manufacturer = "Arduino"

    class SerialFalso:
        is_open = True

        def __init__(self, *_args, **_kwargs):
            self.lineas = [b"EDUTRACK_RFID:INICIADO\n"]

        def readline(self):
            if self.lineas:
                return self.lineas.pop(0)
            raise OSError("USB desconectado")

        def close(self):
            self.is_open = False

    lector = RFIDReader(preferred_port="/dev/ttyACM0")
    with patch("app.rfid_reader.list_ports.comports", return_value=[Puerto()]), \
            patch("app.rfid_reader.Serial", SerialFalso), \
            patch("app.rfid_reader.time.sleep"):
        lector._connect()
        assert lector.status()["conectado"] is True
        # El error de lectura activa el mismo camino que usa el hilo persistente.
        with lector._lock:
            lector._close_locked("Arduino desconectado; buscando el lector nuevamente.")
        assert lector.status()["conectado"] is False
        lector._connect()
        assert lector.status()["conectado"] is True
        lector.stop()
