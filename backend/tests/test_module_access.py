"""Autorización para dashboard/configuración/horarios, sin conexión real."""

import unittest
from datetime import date, datetime, time, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.routes.configuracion import actualizar_plantel, actualizar_preferencias
from app.routes.dashboard import dashboard_tutor
from app.routes.horarios import actualizar_horario, crear_horario, eliminar_horario, listar_horarios
from app.routes.auth import actualizar_perfil
from app.schemas import HorarioActualizar, HorarioCrear, PlantelActualizar, PreferenciasTutor, TutorActualizar


class ModuleAccessTests(unittest.TestCase):
    tutor = {"id": "tutor-auth-id"}
    admin = {"id": "admin-auth-id"}

    def test_admin_cannot_access_tutor_dashboard(self):
        with patch("app.routes.dashboard.obtener_rol", return_value="administrador"):
            with self.assertRaises(HTTPException) as error:
                dashboard_tutor(self.admin)
        self.assertEqual(error.exception.status_code, 403)

    def test_admin_cannot_update_tutor_preferences_or_profile(self):
        with patch("app.routes.configuracion.obtener_rol", return_value="superadministrador"):
            with self.assertRaises(HTTPException) as pref_error:
                actualizar_preferencias(PreferenciasTutor(notificaciones_habilitadas=False), self.admin)
        self.assertEqual(pref_error.exception.status_code, 403)
        with patch("app.routes.auth.obtener_rol", return_value="administrador"):
            with self.assertRaises(HTTPException) as profile_error:
                actualizar_perfil(TutorActualizar(nombre="Admin", telefono=None), self.admin)
        self.assertEqual(profile_error.exception.status_code, 403)

    def test_tutor_profile_update_uses_authenticated_identity(self):
        connection, cursor = self._db((21, "Nombre propio", "5550000", "tutor@example.edu"))
        with patch("app.routes.auth.obtener_rol", return_value="tutor"), patch("app.routes.auth.obtener_conexion", return_value=connection):
            result = actualizar_perfil(TutorActualizar(nombre="Nombre propio", telefono="5550000"), self.tutor)
        self.assertEqual(result["idTutor"], 21)
        self.assertEqual(cursor.execute.call_args.args[1][-1], self.tutor["id"])
        self.assertIn('WHERE auth_user_id=%s', cursor.execute.call_args.args[0])

    def test_tutor_cannot_read_or_change_school_configuration(self):
        with patch("app.routes.configuracion.obtener_rol", return_value="tutor"):
            with self.assertRaises(HTTPException) as error:
                actualizar_plantel(PlantelActualizar(nombre="Plantel", direccion="Calle 1", telefono="12345", correo="plantel@example.edu"), self.tutor)
        self.assertEqual(error.exception.status_code, 403)

    def test_tutor_can_read_schedule_but_cannot_create_or_delete(self):
        with patch("app.routes.horarios.obtener_rol", return_value="tutor"), patch("app.routes.horarios.obtener_conexion") as db:
            db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchall.return_value = []
            self.assertEqual(listar_horarios(self.tutor), [])
            with self.assertRaises(HTTPException) as create_error:
                crear_horario(HorarioCrear(dia_semana="Lunes", grupo="1A", hora_de_entrada="07:00", hora_de_salida="13:00"), self.tutor)
            with self.assertRaises(HTTPException) as delete_error:
                eliminar_horario(1, self.tutor)
            with self.assertRaises(HTTPException) as update_error:
                actualizar_horario(1, HorarioActualizar(grupo="1B"), self.tutor)
        self.assertEqual(create_error.exception.status_code, 403)
        self.assertEqual(delete_error.exception.status_code, 403)
        self.assertEqual(update_error.exception.status_code, 403)

    def _db(self, row=None):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = row
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value = cursor
        return connection, cursor

    def test_admin_can_create_edit_and_delete_schedule(self):
        row = (7, "Lunes", "1A", time(7), time(13), 10)
        connection, cursor = self._db(row)
        with patch("app.routes.horarios.obtener_rol", return_value="administrador"), patch("app.routes.horarios.obtener_conexion", return_value=connection):
            result = crear_horario(HorarioCrear(dia_semana="Lunes", grupo="1A", hora_de_entrada="07:00", hora_de_salida="13:00", tolerancia=10), self.admin)
        self.assertEqual(result["id"], 7)

        edited_row = (7, "Lunes", "1B", time(7), time(13), 10)
        cursor.fetchone.side_effect = [(time(7), time(13)), edited_row]
        with patch("app.routes.horarios.obtener_rol", return_value="superadministrador"), patch("app.routes.horarios.obtener_conexion", return_value=connection):
            edited = actualizar_horario(7, HorarioActualizar(grupo="1B"), self.admin)
        self.assertEqual(edited["grupo"], "1B")
        cursor.rowcount = 1
        with patch("app.routes.horarios.obtener_rol", return_value="administrador"), patch("app.routes.horarios.obtener_conexion", return_value=connection):
            self.assertIsNone(eliminar_horario(7, self.admin))

    def test_tutor_dashboard_query_is_scoped_to_authorized_links(self):
        connection, cursor = self._db()
        cursor.fetchall.side_effect = [
            [(3, "Estudiante vinculado", "M-3", "2A")],
            [(date(2026, 11, 8), datetime(2026, 11, 8, 7, tzinfo=timezone.utc), None, "presente", 3, "Estudiante vinculado", "M-3", "2A")],
        ]
        with patch("app.routes.dashboard.obtener_rol", return_value="tutor"), patch("app.routes.dashboard.obtener_conexion", return_value=connection):
            response = dashboard_tutor(self.tutor)
        self.assertEqual(len(response["estudiantes"]), 1)
        self.assertEqual(response["estudiantes"][0]["id"], 3)
        sql = " ".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertIn('t.auth_user_id=%s', sql)
        self.assertIn('et."Autorizado"=TRUE', sql)


if __name__ == "__main__":
    unittest.main()
