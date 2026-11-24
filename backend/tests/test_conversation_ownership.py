import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from engines.conversation_manager import ConversationManager


class ConversationOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_returns_only_an_existing_owned_session(self):
        conversation = SimpleNamespace(user_id="owner-1", user_deleted=False)
        with patch(
            "engines.conversation_manager.Conversation.find_one",
            new_callable=AsyncMock,
            return_value=conversation,
        ) as find_one:
            result = await ConversationManager().get_session_for_user(
                "session-1", "owner-1"
            )

        self.assertIs(result, conversation)
        find_one.assert_awaited_once()

    async def test_history_hides_foreign_legacy_and_deleted_sessions(self):
        cases = (
            SimpleNamespace(user_id="owner-2", user_deleted=False),
            SimpleNamespace(user_id=None, user_deleted=False),
            SimpleNamespace(user_id="owner-1", user_deleted=True),
            None,
        )
        for conversation in cases:
            with self.subTest(conversation=conversation), patch(
                "engines.conversation_manager.Conversation.find_one",
                new_callable=AsyncMock,
                return_value=conversation,
            ):
                with self.assertRaises(HTTPException) as raised:
                    await ConversationManager().get_session_for_user(
                        "session-1", "owner-1"
                    )
                self.assertEqual(raised.exception.status_code, 404)

    async def test_chat_cannot_claim_an_unowned_legacy_session(self):
        legacy = SimpleNamespace(user_id=None, user_deleted=False)
        with patch(
            "engines.conversation_manager.Conversation.find_one",
            new_callable=AsyncMock,
            return_value=legacy,
        ):
            with self.assertRaises(HTTPException) as raised:
                await ConversationManager().get_or_create_session(
                    "session-1", "owner-1"
                )

        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
