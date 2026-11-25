import unittest
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.asistencia_reglas import clasificar_entrada, siguiente_evento


class AttendanceRuleTests(unittest.TestCase):
    def test_tolerance_boundary_is_inclusive(self):
        zona = ZoneInfo("America/Mexico_City")
        for llegada, esperado in (("06:55", "presente"), ("07:00", "presente"), ("07:10", "presente"), ("07:11", "retardo")):
            with self.subTest(llegada=llegada):
                self.assertEqual(clasificar_entrada(datetime.fromisoformat(f"2026-11-23T{llegada}:00").replace(tzinfo=zona), time(7), 10), esperado)

    def test_first_read_is_entry(self):
        self.assertEqual(siguiente_evento(None, None), "entrada")

    def test_second_read_is_exit(self):
        self.assertEqual(siguiente_evento("08:00", None), "salida")

    def test_further_reads_do_not_change_daily_attendance(self):
        self.assertEqual(siguiente_evento("08:00", "15:00"), "duplicada")


if __name__ == "__main__":
    unittest.main()
