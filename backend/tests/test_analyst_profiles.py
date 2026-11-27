import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from routes.analyst import flagged_conversations, recent_event_profiles, security_events


class _Query:
    def __init__(self, items):
        self.items = items

    def sort(self, *args):
        return self

    def skip(self, *args):
        return self

    def limit(self, *args):
        return self

    async def to_list(self):
        return self.items

    async def count(self):
        return len(self.items)


class AnalystProfileTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = "65a000000000000000000001"
        self.timestamp = datetime(2026, 11, 26, tzinfo=timezone.utc)
        self.user = SimpleNamespace(
            id=self.user_id,
            username="analyst_target",
            display_name="Analyst Target",
            email="target@example.com",
            role="user",
            is_active=True,
            created_at=self.timestamp,
        )
        self.conversation = SimpleNamespace(
            session_id="session-1",
            user_id=self.user_id,
            status="flagged",
            risk_level="high",
            current_risk_score=0.82,
            total_messages=6,
            detection_count=2,
            updated_at=self.timestamp,
        )
        self.event = self._event("event-1", "detection")

    def _event(self, event_id, event_type, timestamp=None):
        return SimpleNamespace(
            id=event_id,
            session_id="session-1",
            event_type=event_type,
            severity="high",
            details={"detection_explanation": "Suspicious prompt"},
            timestamp=timestamp or self.timestamp,
        )

    async def test_security_events_include_linked_conversation_and_profile(self):
        with (
            patch("routes.analyst.SecurityEvent.find", return_value=_Query([self.event])),
            patch("routes.analyst.Conversation.find", return_value=_Query([self.conversation])),
            patch("routes.analyst.User.find", return_value=_Query([self.user])),
        ):
            result = await security_events(
                severity=None,
                skip=0,
                limit=50,
                analyst=SimpleNamespace(role="analyst"),
            )

        self.assertEqual(result["events"][0]["conversation"]["status"], "flagged")
        self.assertEqual(
            result["events"][0]["user_profile"]["display_name"],
            "Analyst Target",
        )

    async def test_flagged_conversations_include_user_and_recent_event_details(self):
        with (
            patch("routes.analyst.Conversation.find", return_value=_Query([self.conversation])),
            patch("routes.analyst.User.find", return_value=_Query([self.user])),
            patch("routes.analyst.SecurityEvent.find", return_value=_Query([self.event])),
        ):
            result = await flagged_conversations(
                skip=0,
                limit=50,
                analyst=SimpleNamespace(role="analyst"),
            )

        flagged = result["conversations"][0]
        self.assertEqual(flagged["user_profile"]["email"], "target@example.com")
        self.assertEqual(flagged["recent_security_events"][0]["event_type"], "detection")

    async def test_profiles_are_unique_and_ordered_by_latest_security_event(self):
        older_event = self._event(
            "event-older",
            "risk_escalation",
            datetime(2026, 11, 25, tzinfo=timezone.utc),
        )
        with (
            patch(
                "routes.analyst.SecurityEvent.find_all",
                return_value=_Query([self.event, older_event]),
            ),
            patch("routes.analyst.Conversation.find", return_value=_Query([self.conversation])),
            patch("routes.analyst.User.find", return_value=_Query([self.user])),
        ):
            result = await recent_event_profiles(
                limit=100,
                analyst=SimpleNamespace(role="analyst"),
            )

        self.assertEqual(result["total"], 1)
        self.assertEqual(len(result["profiles"]), 1)
        profile = result["profiles"][0]
        self.assertEqual(profile["latest_event"]["id"], "event-1")
        self.assertEqual(profile["security_event_count"], 2)


if __name__ == "__main__":
    unittest.main()
