import unittest

from fastapi import HTTPException

from app.routes.horarios import _normalizar_dia


class DiasHorarioTests(unittest.TestCase):
    def test_acepta_miercoles_con_o_sin_acento_y_mayusculas(self):
        self.assertEqual(_normalizar_dia("miércoles"), "miercoles")
        self.assertEqual(_normalizar_dia("MIERCOLES"), "miercoles")

    def test_rechaza_un_dia_que_no_pertenece_a_la_semana(self):
        with self.assertRaises(HTTPException) as error:
            _normalizar_dia("día escolar")
        self.assertEqual(error.exception.status_code, 422)
