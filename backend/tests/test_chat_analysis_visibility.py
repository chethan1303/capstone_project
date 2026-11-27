import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from routes.chat import ChatRequest, chat, get_history, router
from services.llm_service import LLMResult


class ChatAnalysisVisibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_response_hides_analysis_from_users(self):
        conversation = SimpleNamespace(messages=[])
        detection = SimpleNamespace(
            is_suspicious=False,
            signals=SimpleNamespace(),
            explanation="internal detection explanation",
        )
        risk = SimpleNamespace(
            level="high",
            current_score=0.9,
            delta=0.9,
            turn_number=1,
            contributing_factors=["internal signal"],
        )
        defense = SimpleNamespace(
            action="restrict",
            response_override=None,
            modified_system_prompt="internal defense prompt",
        )
        llm = SimpleNamespace(
            generate_response=AsyncMock(
                return_value=LLMResult(
                    content="Reply",
                    prompt_tokens=12,
                    completion_tokens=4,
                )
            )
        )
        with (
            patch(
                "routes.chat.conversation_mgr.get_or_create_session",
                new_callable=AsyncMock,
                return_value=conversation,
            ),
            patch(
                "routes.chat.conversation_mgr.add_message",
                new_callable=AsyncMock,
                return_value=conversation,
            ),
            patch(
                "routes.chat.conversation_mgr.update_risk",
                new_callable=AsyncMock,
                return_value=conversation,
            ),
            patch("routes.chat.detection_engine.analyze", return_value=detection),
            patch("routes.chat.risk_engine.assess", return_value=risk),
            patch("routes.chat.defense_engine.apply_policy", return_value=defense),
            patch("routes.chat.get_llm_service", return_value=llm),
        ):
            user_response = await chat(
                ChatRequest(session_id="session-1", message="Hello"),
                SimpleNamespace(id="user-1", role="user"),
            )
            admin_response = await chat(
                ChatRequest(session_id="session-2", message="Hello"),
                SimpleNamespace(id="admin-1", role="admin"),
            )

        self.assertEqual(
            user_response.model_dump(exclude_none=True),
            {"response": "Reply", "session_id": "session-1"},
        )
        self.assertEqual(admin_response.risk_score, 0.9)
        self.assertEqual(admin_response.detection_explanation, detection.explanation)
        post_route = next(
            route for route in router.routes if "POST" in route.methods
        )
        self.assertTrue(post_route.response_model_exclude_none)

    async def test_history_hides_analysis_from_users_only(self):
        message = SimpleNamespace(
            role="user",
            content="Hello",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            detection_result=SimpleNamespace(
                model_dump=lambda: {"overall_suspicion": 0.9}
            ),
            risk_score_after=0.9,
            defense_action="restrict",
            prompt_tokens=None,
            completion_tokens=None,
        )
        conversation = SimpleNamespace(messages=[message])
        with patch(
            "routes.chat.conversation_mgr.get_session_for_user",
            new_callable=AsyncMock,
            return_value=conversation,
        ):
            user_history = await get_history(
                "session-1", SimpleNamespace(id="user-1", role="user")
            )
            admin_history = await get_history(
                "session-1", SimpleNamespace(id="admin-1", role="admin")
            )

        self.assertEqual(
            set(user_history[0]),
            {"role", "content", "timestamp"},
        )
        self.assertIn("detection_result", admin_history[0])
        self.assertIn("risk_score_after", admin_history[0])

    async def test_block_policy_without_response_fails_explicitly(self):
        conversation = SimpleNamespace(messages=[])
        detection = SimpleNamespace(
            is_suspicious=True,
            signals=SimpleNamespace(),
            explanation="blocked",
        )
        risk = SimpleNamespace(
            level="critical",
            current_score=1.0,
            delta=1.0,
            turn_number=1,
            contributing_factors=[],
        )
        defense = SimpleNamespace(
            action="block",
            response_override=None,
            modified_system_prompt=None,
        )
        with (
            patch(
                "routes.chat.conversation_mgr.get_or_create_session",
                new_callable=AsyncMock,
                return_value=conversation,
            ),
            patch("routes.chat.detection_engine.analyze", return_value=detection),
            patch("routes.chat.risk_engine.assess", return_value=risk),
            patch("routes.chat.defense_engine.apply_policy", return_value=defense),
        ):
            with self.assertRaises(HTTPException) as error:
                await chat(
                    ChatRequest(session_id="session-1", message="Hello"),
                    SimpleNamespace(id="user-1", role="user"),
                )

        self.assertEqual(error.exception.status_code, 500)


if __name__ == "__main__":
    unittest.main()
