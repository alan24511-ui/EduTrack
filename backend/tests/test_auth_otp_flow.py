"""Regresión del contrato OTP con Supabase Auth."""

import unittest
from unittest.mock import MagicMock, patch

from app import supabase_auth


class SupabaseOtpRequestTests(unittest.TestCase):
    def _post(self, expected_path: str, function, *args):
        response = MagicMock()
        response.status_code = 200
        response.content = b'{"user": {"id": "user-1"}}'
        response.json.return_value = {"user": {"id": "user-1"}}
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response

        with patch.object(supabase_auth, "_url_base", return_value="https://example.supabase.co/auth/v1"), \
                patch.object(supabase_auth, "_encabezados", return_value={"apikey": "anon"}), \
                patch.object(supabase_auth.httpx, "Client", return_value=client):
            function(*args)

        self.assertTrue(client.post.call_args.args[0].endswith(expected_path))
        return client.post.call_args.kwargs["json"]

    def test_signup_registration_does_not_request_a_magic_link_redirect(self):
        body = self._post("/signup", supabase_auth.registrar_usuario, "tutor@example.com", "password", "Tutor")
        self.assertEqual(body, {"email": "tutor@example.com", "password": "password", "data": {"nombre": "Tutor"}})

    def test_signup_and_recovery_use_their_supabase_verify_types(self):
        signup = self._post("/verify", supabase_auth.verificar_otp, "tutor@example.com", "123456")
        recovery = self._post("/verify", supabase_auth.verificar_otp, "tutor@example.com", "654321", "recovery")
        self.assertEqual(signup["type"], "signup")
        self.assertEqual(recovery["type"], "recovery")

    def test_resend_forwards_supabase_signup_and_recovery_types(self):
        signup = self._post("/resend", supabase_auth.reenviar_otp, "tutor@example.com", "signup")
        recovery = self._post("/resend", supabase_auth.reenviar_otp, "tutor@example.com", "recovery")
        self.assertEqual(signup, {"type": "signup", "email": "tutor@example.com"})
        self.assertEqual(recovery, {"type": "recovery", "email": "tutor@example.com"})


if __name__ == "__main__":
    unittest.main()
