"""Pruebas de autorización sin usuarios ni base de datos reales."""

import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.routes.vinculacion import _validar_tutor, router as vinculacion_router
from app.security import usuario_actual


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

    def test_linking_exposes_search_and_confirmation_routes_only(self):
        self.assertEqual(
            {route.path for route in vinculacion_router.routes},
            {"/buscar", "/confirmar"},
        )

    def test_linking_is_exclusive_to_the_authenticated_tutor(self):
        with patch("app.routes.vinculacion.obtener_rol", return_value="tutor"):
            with patch("app.routes.vinculacion._obtener_id_tutor", return_value=7):
                self.assertEqual(_validar_tutor(self.usuario_tutor), 7)

        with patch("app.routes.vinculacion.obtener_rol", return_value="administrador"):
            with self.assertRaises(HTTPException) as error:
                _validar_tutor(self.usuario_admin)
        self.assertEqual(error.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
