import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from create_admin import validate_admin_input
from create_admin import create_first_admin
from pymongo.errors import DuplicateKeyError


class AdminBootstrapTests(unittest.IsolatedAsyncioTestCase):
    def test_bootstrap_normalizes_account_identifiers(self):
        username, email = validate_admin_input(
            "  first_admin ",
            " ADMIN@EXAMPLE.COM ",
            "correct horse battery staple",
            "correct horse battery staple",
        )

        self.assertEqual(username, "first_admin")
        self.assertEqual(email, "admin@example.com")

    def test_bootstrap_rejects_short_or_oversized_passwords(self):
        for password in ("short", "é" * 37):
            with self.subTest(password_length=len(password)), self.assertRaises(ValueError):
                validate_admin_input(
                    "first_admin",
                    "admin@example.com",
                    password,
                    password,
                )

    async def test_bootstrap_refuses_to_repeat_a_completed_bootstrap(self):
        collection = MagicMock()
        collection.insert_one = AsyncMock(side_effect=DuplicateKeyError("already bootstrapped"))
        with patch(
            "create_admin.User.get_motor_collection",
            return_value=MagicMock(database={"admin_bootstrap": collection}),
        ):
            with self.assertRaisesRegex(ValueError, "already been completed"):
                await create_first_admin(
                    "first_admin",
                    "admin@example.com",
                    "correct horse battery staple",
                    "correct horse battery staple",
                )

        collection.insert_one.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
