import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from routes.auth import RegisterRequest
from routes.chat import ChatRequest
from routes.auth import _login
from services.auth_service import get_current_chat_user, get_current_user
from fastapi import HTTPException
from unittest.mock import patch


class AuthValidationTests(unittest.IsolatedAsyncioTestCase):
    def test_registration_normalizes_username_and_email(self):
        body = RegisterRequest(
            username="  analyst_1 ",
            email="  Analyst@Example.COM ",
            password="long-enough-passphrase",
        )

        self.assertEqual(body.username, "analyst_1")
        self.assertEqual(body.email, "analyst@example.com")

    def test_registration_rejects_bad_email_and_bcrypt_oversized_password(self):
        with self.assertRaises(ValidationError):
            RegisterRequest(
                username="analyst",
                email="not-an-email",
                password="long-enough-passphrase",
            )
        with self.assertRaises(ValidationError):
            RegisterRequest(
                username="analyst",
                email="analyst@example.com",
                password="é" * 37,
            )

    def test_chat_rejects_blank_session_and_message(self):
        for values in (
            {"session_id": "   ", "message": "hello"},
            {"session_id": "session-1", "message": "  "},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ChatRequest(**values)

    async def test_token_subject_must_be_a_nonempty_string(self):
        with patch(
            "services.auth_service.decode_access_token",
            return_value={"sub": ["admin"]},
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_current_user("token")

        self.assertEqual(raised.exception.status_code, 401)

    async def test_disabled_account_cannot_use_an_existing_token(self):
        from types import SimpleNamespace

        with (
            patch(
                "services.auth_service.decode_access_token",
                return_value={"sub": "analyst"},
            ),
            patch(
                "services.auth_service.User.find_one",
                new_callable=AsyncMock,
                return_value=SimpleNamespace(is_active=False),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_current_user("token")

        self.assertEqual(raised.exception.status_code, 401)

    async def test_login_rejects_bcrypt_oversized_password_before_lookup(self):
        from types import SimpleNamespace

        with patch("routes.auth.User.find_one") as find_one:
            with self.assertRaises(HTTPException) as raised:
                await _login(
                    SimpleNamespace(username="analyst", password="é" * 37),
                    required_role="user",
                )

        self.assertEqual(raised.exception.status_code, 401)
        find_one.assert_not_called()

    async def test_disabled_account_cannot_log_in(self):
        from types import SimpleNamespace

        with patch(
            "routes.auth.User.find_one",
            new_callable=AsyncMock,
            return_value=SimpleNamespace(is_active=False),
        ), patch("routes.auth.verify_password") as verify_password:
            with self.assertRaises(HTTPException) as raised:
                await _login(
                    SimpleNamespace(username="analyst", password="valid-password"),
                    required_role="user",
                )

        self.assertEqual(raised.exception.status_code, 401)
        verify_password.assert_not_called()

    async def test_analysts_can_access_chat_but_unrecognized_roles_cannot(self):
        analyst = SimpleNamespace(role="analyst")
        self.assertIs(await get_current_chat_user(analyst), analyst)

        with self.assertRaises(HTTPException) as raised:
            await get_current_chat_user(SimpleNamespace(role="service"))

        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
