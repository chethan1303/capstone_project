import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from routes.admin import list_all_conversations


class AdminConversationFilterTests(unittest.IsolatedAsyncioTestCase):
    async def test_filters_are_combined_and_session_search_is_escaped(self):
        query = MagicMock()
        query.sort.return_value = query
        query.skip.return_value = query
        query.limit.return_value = query
        query.to_list = AsyncMock(return_value=[])
        query.count = AsyncMock(return_value=0)

        with patch("routes.admin.Conversation.find", return_value=query) as find:
            response = await list_all_conversations(
                status="flagged",
                risk_level="high",
                session_id="abc.*",
                admin=MagicMock(),
            )

        expected_filter = {
            "status": "flagged",
            "risk_level": "high",
            "session_id": {"$regex": r"abc\.\*", "$options": "i"},
        }
        self.assertEqual(response["total"], 0)
        self.assertEqual(find.call_args_list[0].args[0], expected_filter)
        self.assertEqual(find.call_args_list[1].args[0], expected_filter)


if __name__ == "__main__":
    unittest.main()
