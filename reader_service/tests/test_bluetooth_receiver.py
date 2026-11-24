import unittest

from bluetooth_receiver import BluetoothReceiver, extraer_uid


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
        self.assertEqual(len(session.calls), 1)
        args, kwargs = session.calls[0]
        self.assertEqual(args[0], "http://localhost:8000/rfid/lecturas")
        self.assertEqual(kwargs["json"], {"uid": "04AABBCC", "codigo_dispositivo": "lector-prueba"})
        self.assertEqual(kwargs["headers"]["X-Reader-Token"], "token")


if __name__ == "__main__":
    unittest.main()
