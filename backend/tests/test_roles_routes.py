import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from routes.roles import (
    UserActiveUpdateRequest,
    UserRoleUpdateRequest,
    deactivate_user,
    list_users,
    update_user_active,
    update_user_role,
)
from main import app


class RoleManagementTests(unittest.IsolatedAsyncioTestCase):
    def test_role_management_routes_are_mounted(self):
        routes = {
            (route.path, method)
            for route in app.routes
            if hasattr(route, "methods")
            for method in route.methods
        }

        self.assertIn(("/api/admin/users", "GET"), routes)
        self.assertIn(("/api/admin/users/{username}", "DELETE"), routes)
        self.assertIn(("/api/admin/users/{username}/active", "PATCH"), routes)
        self.assertIn(("/api/admin/users/{username}/role", "PATCH"), routes)

    async def test_list_users_includes_active_status_without_password_hash(self):
        user = SimpleNamespace(
            username="alice",
            email="alice@example.com",
            role="analyst",
            is_active=False,
            created_at=MagicMock(isoformat=lambda: "2026-01-01T00:00:00+00:00"),
            hashed_password="must-not-leak",
        )
        query = MagicMock()
        query.sort.return_value = query
        query.to_list = AsyncMock(return_value=[user])

        with patch("routes.roles.User.find_all", return_value=query):
            result = await list_users(MagicMock())

        self.assertEqual(result[0]["is_active"], False)
        self.assertNotIn("hashed_password", result[0])

    async def test_deactivation_preserves_account_and_marks_it_inactive(self):
        user = SimpleNamespace(
            username="alice",
            role="user",
            is_active=True,
            save=AsyncMock(),
        )
        with patch(
            "routes.roles.User.find_one",
            new_callable=AsyncMock,
            return_value=user,
        ):
            result = await deactivate_user("alice", MagicMock(username="admin"))

        self.assertFalse(user.is_active)
        user.save.assert_awaited_once()
        self.assertFalse(result["is_active"])
        self.assertIn("history was retained", result["detail"])

    async def test_admin_cannot_deactivate_self_or_last_active_admin(self):
        self_admin = SimpleNamespace(
            username="admin",
            role="admin",
            is_active=True,
            save=AsyncMock(),
        )
        with patch(
            "routes.roles.User.find_one",
            new_callable=AsyncMock,
            return_value=self_admin,
        ):
            with self.assertRaises(HTTPException) as raised:
                await deactivate_user("admin", MagicMock(username="admin"))
        self.assertEqual(raised.exception.status_code, 409)
        self_admin.save.assert_not_awaited()

        last_admin = SimpleNamespace(
            username="last_admin",
            role="admin",
            is_active=True,
            save=AsyncMock(),
        )
        admin_query = MagicMock()
        admin_query.count = AsyncMock(return_value=1)
        expected_admin_filter = {
            "role": "admin",
            "$or": [
                {"is_active": True},
                {"is_active": {"$exists": False}},
            ],
        }
        with (
            patch(
                "routes.roles.User.find_one",
                new_callable=AsyncMock,
                return_value=last_admin,
            ),
            patch("routes.roles.User.find", return_value=admin_query) as find_admins,
        ):
            with self.assertRaises(HTTPException) as raised:
                await deactivate_user("last_admin", MagicMock(username="other_admin"))

        self.assertEqual(raised.exception.status_code, 409)
        find_admins.assert_called_once_with(expected_admin_filter)
        last_admin.save.assert_not_awaited()

    async def test_last_active_admin_cannot_be_demoted(self):
        last_admin = SimpleNamespace(
            username="last_admin",
            role="admin",
            is_active=True,
            save=AsyncMock(),
        )
        admin_query = MagicMock()
        admin_query.count = AsyncMock(return_value=1)
        with (
            patch(
                "routes.roles.User.find_one",
                new_callable=AsyncMock,
                return_value=last_admin,
            ),
            patch("routes.roles.User.find", return_value=admin_query),
        ):
            with self.assertRaises(HTTPException) as raised:
                await update_user_role(
                    "last_admin",
                    UserRoleUpdateRequest(role="analyst"),
                    admin=MagicMock(username="other_admin"),
                )

        self.assertEqual(raised.exception.status_code, 409)
        last_admin.save.assert_not_awaited()

    async def test_administrator_can_reactivate_a_disabled_user(self):
        user = SimpleNamespace(
            username="alice",
            is_active=False,
            save=AsyncMock(),
        )
        with patch(
            "routes.roles.User.find_one",
            new_callable=AsyncMock,
            return_value=user,
        ):
            result = await update_user_active(
                "alice",
                UserActiveUpdateRequest(is_active=True),
                admin=MagicMock(username="admin"),
            )

        self.assertTrue(user.is_active)
        user.save.assert_awaited_once()
        self.assertTrue(result["is_active"])


if __name__ == "__main__":
    unittest.main()
