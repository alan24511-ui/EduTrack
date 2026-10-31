"""Pruebas de autorización sin usuarios ni base de datos reales."""

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.routes.vinculacion import generar_codigo_vinculacion, router as vinculacion_router
from app.schemas import GenerarCodigoEntrada
from app.security import es_administrador, usuario_actual, usuario_administrador


class RoleAccessTests(unittest.TestCase):
    def setUp(self):
        self.usuario_tutor = {
            "id": "test-tutor-id",
            "email_confirmed_at": "2026-01-01T00:00:00Z",
        }
        self.usuario_admin = {
            "id": "test-admin-id",
            "email_confirmed_at": "2026-01-01T00:00:00Z",
        }

    def test_admin_endpoint_requires_a_session(self):
        with self.assertRaises(HTTPException) as error:
            usuario_actual("")
        self.assertEqual(error.exception.status_code, 401)

    def test_invalid_token_returns_401(self):
        with patch(
            "app.security.obtener_usuario",
            side_effect=HTTPException(status_code=401, detail="invalid token"),
        ):
            with self.assertRaises(HTTPException) as error:
                usuario_actual("Bearer token-invalido")
        self.assertEqual(error.exception.status_code, 401)

    def test_admin_role_lookup_uses_authenticated_auth_id(self):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (1,)
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value = cursor

        with patch("app.security.obtener_conexion", return_value=connection):
            self.assertTrue(es_administrador("auth-user-from-verified-token"))

        cursor.execute.assert_called_once_with(
            'SELECT 1 FROM "Administradores" WHERE auth_user_id = %s',
            ("auth-user-from-verified-token",),
        )

    def test_tutor_cannot_generate_code_even_with_client_admin_claim(self):
        with patch("app.security.es_administrador", return_value=False):
            with self.assertRaises(HTTPException) as error:
                usuario_administrador(self.usuario_tutor)
        self.assertEqual(error.exception.status_code, 403)

        endpoint = next(
            route for route in vinculacion_router.routes if route.path.endswith("/codigos")
        )
        self.assertIn(
            usuario_administrador,
            [dependencia.call for dependencia in endpoint.dependant.dependencies],
        )

    def test_admin_can_generate_code(self):
        with patch("app.security.es_administrador", return_value=True):
            usuario = usuario_administrador(self.usuario_admin)
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.side_effect = [
            (41,),
            (9, datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc)),
        ]
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value = cursor

        with (
            patch("app.routes.vinculacion.obtener_conexion", return_value=connection),
            patch(
                "app.routes.vinculacion.obtener_settings",
                return_value=SimpleNamespace(vinculacion_codigo_expiracion_minutos=15),
            ),
            patch("app.routes.vinculacion.generar_codigo", return_value="ABCDEFGHJKLM"),
            patch("app.routes.vinculacion.hashear_codigo", return_value="hash"),
        ):
            response = generar_codigo_vinculacion(
                GenerarCodigoEntrada(matricula="A-1"),
                usuario,
            )

        self.assertEqual(response["codigo"], "ABCDEFGHJKLM")
        self.assertEqual(response["id_codigo"], 9)


if __name__ == "__main__":
    unittest.main()
