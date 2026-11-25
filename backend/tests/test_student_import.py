import unittest

from app.routes.estudiantes import _analizar_filas


class StudentImportTests(unittest.TestCase):
    def test_importacion_valida_compone_campos_requeridos_y_grupo_existente(self):
        filas = _analizar_filas(
            [["Matrícula", "Nombre", "Apellidos", "Grupo"], ["M100", "Ana", "Pérez", "A"]],
            set(), {"a"},
        )
        self.assertTrue(filas[0]["valida"])
        self.assertEqual(filas[0]["nombre"], "Ana")


    def test_importacion_marca_duplicados_y_grupos_inexistentes_por_fila(self):
        filas = _analizar_filas(
            [["Matricula", "Nombre", "Apellidos", "Grupo"], ["M100", "Ana", "Pérez", "A"], ["M100", "Luis", "López", "B"]],
            {"ya-existe"}, {"a"},
        )
        self.assertTrue(filas[0]["valida"])
        self.assertIn("La matrícula está duplicada en el archivo.", filas[1]["errores"])
        self.assertIn("El grupo no existe en EduTrack.", filas[1]["errores"])


    def test_importacion_detecta_matricula_ya_registrada(self):
        filas = _analizar_filas(
            [["Matricula", "Nombre", "Apellidos", "Grupo"], ["M100", "Ana", "Pérez", "A"]],
            {"m100"}, {"a"},
        )
        self.assertFalse(filas[0]["valida"])
        self.assertIn("La matrícula ya existe.", filas[0]["errores"])


    def test_apellidos_es_opcional_por_el_modelo_de_nombre_completo(self):
        filas = _analizar_filas(
            [["Matrícula", "Nombre", "Grupo"], ["M101", "Ana Pérez", "A"]],
            set(), {"a"},
        )
        self.assertTrue(filas[0]["valida"])
        self.assertEqual(filas[0]["apellidos"], "")
