import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from google.auth.exceptions import TransportError
from pymongo.errors import DuplicateKeyError

from routes.auth import GoogleLoginRequest, google_login
from services.google_auth_service import authenticate_google_credential


class GoogleAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_google_sign_in_requires_server_client_id_configuration(self):
        with (
            patch("services.google_auth_service.settings.GOOGLE_CLIENT_ID", ""),
            patch("services.google_auth_service.run_in_threadpool") as verify,
        ):
            with self.assertRaises(HTTPException) as raised:
                await authenticate_google_credential("credential")

        self.assertEqual(raised.exception.status_code, 503)
        verify.assert_not_called()

    async def test_invalid_google_credential_is_rejected(self):
        with (
            patch("services.google_auth_service.settings.GOOGLE_CLIENT_ID", "client-id"),
            patch(
                "services.google_auth_service.run_in_threadpool",
                new_callable=AsyncMock,
                side_effect=ValueError("invalid token"),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await authenticate_google_credential("invalid-credential")

        self.assertEqual(raised.exception.status_code, 401)

    async def test_unverified_google_email_is_rejected_before_account_lookup(self):
        with (
            patch("services.google_auth_service.settings.GOOGLE_CLIENT_ID", "client-id"),
            patch(
                "services.google_auth_service.run_in_threadpool",
                new_callable=AsyncMock,
                return_value={
                    "sub": "google-subject",
                    "email": "person@example.com",
                    "email_verified": False,
                },
            ),
            patch("services.google_auth_service.User.find_one", new_callable=AsyncMock) as find_one,
        ):
            with self.assertRaises(HTTPException) as raised:
                await authenticate_google_credential("credential")

        self.assertEqual(raised.exception.status_code, 401)
        find_one.assert_not_awaited()

    async def test_new_google_account_is_always_created_as_standard_user(self):
        with (
            patch("services.google_auth_service.settings.GOOGLE_CLIENT_ID", "client-id"),
            patch(
                "services.google_auth_service.run_in_threadpool",
                new_callable=AsyncMock,
                return_value={
                    "sub": "google-subject",
                    "email": "Person@Example.com",
                    "email_verified": True,
                    "name": "Person Example",
                    "role": "admin",
                },
            ),
            patch(
                "services.google_auth_service.User.find_one",
                new_callable=AsyncMock,
                side_effect=[None, None],
            ),
            patch("services.google_auth_service.hash_password", return_value="hashed"),
            patch(
                "services.google_auth_service.User.get_motor_collection",
                return_value=None,
            ),
            patch("services.google_auth_service.User.insert", new_callable=AsyncMock) as insert,
        ):
            user = await authenticate_google_credential("credential")

        self.assertEqual(user.role, "user")
        self.assertEqual(user.email, "person@example.com")
        self.assertEqual(user.display_name, "Person Example")
        self.assertEqual(user.google_subject, "google-subject")
        insert.assert_awaited_once()

    async def test_existing_google_user_display_name_is_updated_from_verified_claims(self):
        user = SimpleNamespace(
            is_active=True,
            role="user",
            display_name=None,
            save=AsyncMock(),
        )
        with (
            patch("services.google_auth_service.settings.GOOGLE_CLIENT_ID", "client-id"),
            patch(
                "services.google_auth_service.run_in_threadpool",
                new_callable=AsyncMock,
                return_value={
                    "sub": "google-subject",
                    "email": "person@example.com",
                    "email_verified": True,
                    "name": "Person Example",
                },
            ),
            patch(
                "services.google_auth_service.User.find_one",
                new_callable=AsyncMock,
                return_value=user,
            ),
        ):
            result = await authenticate_google_credential("credential")

        self.assertIs(result, user)
        self.assertEqual(user.display_name, "Person Example")
        user.save.assert_awaited_once()

    async def test_existing_email_is_not_automatically_linked(self):
        existing_user = SimpleNamespace(username="local-user", role="user")
        with (
            patch("services.google_auth_service.settings.GOOGLE_CLIENT_ID", "client-id"),
            patch(
                "services.google_auth_service.run_in_threadpool",
                new_callable=AsyncMock,
                return_value={
                    "sub": "google-subject",
                    "email": "person@example.com",
                    "email_verified": True,
                },
            ),
            patch(
                "services.google_auth_service.User.find_one",
                new_callable=AsyncMock,
                side_effect=[None, existing_user],
            ),
            patch("services.google_auth_service.User.insert", new_callable=AsyncMock) as insert,
        ):
            with self.assertRaises(HTTPException) as raised:
                await authenticate_google_credential("credential")

        self.assertEqual(raised.exception.status_code, 409)
        insert.assert_not_awaited()

    async def test_existing_privileged_or_inactive_google_identity_is_rejected(self):
        for user in (
            SimpleNamespace(is_active=True, role="admin"),
            SimpleNamespace(is_active=False, role="user"),
        ):
            with (
                self.subTest(user=user),
                patch("services.google_auth_service.settings.GOOGLE_CLIENT_ID", "client-id"),
                patch(
                    "services.google_auth_service.run_in_threadpool",
                    new_callable=AsyncMock,
                    return_value={
                        "sub": "google-subject",
                        "email": "person@example.com",
                        "email_verified": True,
                    },
                ),
                patch(
                    "services.google_auth_service.User.find_one",
                    new_callable=AsyncMock,
                    return_value=user,
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    await authenticate_google_credential("credential")

                self.assertEqual(raised.exception.status_code, 401)

    async def test_google_verification_outage_is_reported_as_service_unavailable(self):
        with (
            patch("services.google_auth_service.settings.GOOGLE_CLIENT_ID", "client-id"),
            patch(
                "services.google_auth_service.run_in_threadpool",
                new_callable=AsyncMock,
                side_effect=TransportError("certificate service unavailable"),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await authenticate_google_credential("credential")

        self.assertEqual(raised.exception.status_code, 503)

    async def test_duplicate_google_signup_returns_the_created_standard_account(self):
        created_account = SimpleNamespace(
            is_active=True,
            role="user",
            display_name="person",
            save=AsyncMock(),
        )
        with (
            patch("services.google_auth_service.settings.GOOGLE_CLIENT_ID", "client-id"),
            patch(
                "services.google_auth_service.run_in_threadpool",
                new_callable=AsyncMock,
                return_value={
                    "sub": "google-subject",
                    "email": "person@example.com",
                    "email_verified": True,
                },
            ),
            patch(
                "services.google_auth_service.User.find_one",
                new_callable=AsyncMock,
                side_effect=[None, None, created_account],
            ),
            patch(
                "services.google_auth_service.User.get_motor_collection",
                return_value=None,
            ),
            patch(
                "services.google_auth_service.User.insert",
                new_callable=AsyncMock,
                side_effect=DuplicateKeyError("duplicate signup"),
            ),
        ):
            user = await authenticate_google_credential("credential")

        self.assertIs(user, created_account)

    async def test_google_login_route_never_issues_tokens_for_privileged_users(self):
        with (
            patch(
                "routes.auth.authenticate_google_credential",
                new_callable=AsyncMock,
                return_value=SimpleNamespace(role="admin"),
            ),
            patch("routes.auth.create_access_token") as create_token,
        ):
            with self.assertRaises(HTTPException) as raised:
                await google_login(GoogleLoginRequest(credential="credential"))

        self.assertEqual(raised.exception.status_code, 403)
        create_token.assert_not_called()

    async def test_google_login_route_issues_token_for_standard_user(self):
        with (
            patch(
                "routes.auth.authenticate_google_credential",
                new_callable=AsyncMock,
                return_value=SimpleNamespace(role="user", username="google_user"),
            ),
            patch("routes.auth.create_access_token", return_value="app-token") as create_token,
        ):
            response = await google_login(GoogleLoginRequest(credential="credential"))

        self.assertEqual(response.access_token, "app-token")
        create_token.assert_called_once_with(data={"sub": "google_user"})


if __name__ == "__main__":
    unittest.main()
