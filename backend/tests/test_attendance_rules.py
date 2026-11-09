import unittest

from app.asistencia_reglas import siguiente_evento


class AttendanceRuleTests(unittest.TestCase):
    def test_first_read_is_entry(self):
        self.assertEqual(siguiente_evento(None, None), "entrada")

    def test_second_read_is_exit(self):
        self.assertEqual(siguiente_evento("08:00", None), "salida")

    def test_further_reads_do_not_change_daily_attendance(self):
        self.assertEqual(siguiente_evento("08:00", "15:00"), "duplicada")


if __name__ == "__main__":
    unittest.main()
