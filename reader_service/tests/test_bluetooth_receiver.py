import unittest
from unittest.mock import patch
import sys

from bluetooth_receiver import BluetoothReceiver, extraer_uid, main


class Response:
    def raise_for_status(self):
        pass

    def json(self):
        return {"resultado": "ENTRADA_REGISTRADA", "mensaje": "Entrada registrada."}


class Session:
    def __init__(self):
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return Response()


class BluetoothReceiverTests(unittest.TestCase):
    def test_no_inicia_sin_token_de_ingesta(self):
        with patch.dict("os.environ", {"EDUTRACK_DEVICE_CODE": "lector-prueba"}, clear=True):
            with patch.object(sys, "argv", ["bluetooth_receiver.py"]):
                with self.assertRaises(SystemExit) as error:
                    main()
        self.assertEqual(error.exception.code, 2)

    def test_extrae_y_valida_uids(self):
        self.assertEqual(extraer_uid("UID:04aabbcc\r\n"), "04AABBCC")
        self.assertEqual(extraer_uid("UID:04112233"), "04112233")
        self.assertIsNone(extraer_uid("UID:1234"))
        self.assertIsNone(extraer_uid("diagnóstico"))

    def test_envia_al_endpoint_existente_y_suprime_repeticion(self):
        receiver = BluetoothReceiver("/dev/rfcomm0", 9600, "http://localhost:8000",
                                     "lector-prueba", "token")
        session = Session()
        self.assertTrue(receiver.procesar_linea("UID:04AABBCC", session))
        self.assertFalse(receiver.procesar_linea("UID:04AABBCC", session))
        self.assertEqual(len(session.calls), 3)
        args, kwargs = session.calls[1]
        self.assertEqual(args[0], "http://localhost:8000/rfid/lecturas")
        self.assertEqual(kwargs["json"], {"uid": "04AABBCC", "codigo_dispositivo": "lector-prueba"})
        self.assertEqual(kwargs["headers"]["X-Ingesta-Token"], "token")
        self.assertEqual(session.calls[0][1]["headers"]["X-Reader-Token"], "token")


if __name__ == "__main__":
    unittest.main()
