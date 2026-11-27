import csv
import io
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from services.conversation_metrics import calculate_conversation_metrics
from services.report_service import build_csv, build_pdf


class ConversationMetricsTests(unittest.TestCase):
    def test_metrics_sum_provider_usage_and_utf8_message_bytes(self):
        conversation = SimpleNamespace(messages=[
            SimpleNamespace(
                role="user",
                content="Hi",
                prompt_tokens=None,
                completion_tokens=None,
            ),
            SimpleNamespace(
                role="assistant",
                content="Café",
                prompt_tokens=9,
                completion_tokens=3,
            ),
            SimpleNamespace(
                role="assistant",
                content="Done",
                prompt_tokens=5,
                completion_tokens=2,
            ),
        ])

        metrics = calculate_conversation_metrics(conversation)

        self.assertEqual(metrics.prompt_tokens, 14)
        self.assertEqual(metrics.completion_tokens, 5)
        self.assertEqual(metrics.total_tokens, 19)
        self.assertTrue(metrics.token_usage_complete)
        self.assertEqual(metrics.message_text_bytes, 11)

    def test_legacy_sessions_report_usage_as_incomplete(self):
        conversation = SimpleNamespace(messages=[
            SimpleNamespace(
                role="assistant",
                content="old message",
                prompt_tokens=None,
                completion_tokens=None,
            )
        ])

        metrics = calculate_conversation_metrics(conversation)

        self.assertFalse(metrics.token_usage_complete)
        self.assertIsNone(metrics.total_tokens)
        self.assertEqual(metrics.message_text_bytes, 11)

    def test_csv_report_includes_session_and_message_metrics(self):
        message = SimpleNamespace(
            role="assistant",
            content="Café",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            risk_score_after=None,
            defense_action=None,
            detection_result=None,
            prompt_tokens=9,
            completion_tokens=3,
        )
        conversation = SimpleNamespace(
            session_id="session-1",
            user_id="user-1",
            status="active",
            risk_level="low",
            current_risk_score=0.1,
            detection_count=0,
            total_messages=1,
            messages=[message],
        )

        rows = list(csv.reader(io.StringIO(build_csv([conversation]).decode("utf-8-sig"))))
        headers = rows[0]
        data = dict(zip(headers, rows[1]))

        self.assertEqual(data["prompt_tokens"], "9")
        self.assertEqual(data["completion_tokens"], "3")
        self.assertEqual(data["total_tokens"], "12")
        self.assertEqual(data["token_usage_complete"], "True")
        self.assertEqual(data["message_text_bytes"], "5")
        self.assertEqual(data["message_completion_tokens"], "3")

    def test_pdf_report_generates_with_session_metrics(self):
        conversation = SimpleNamespace(
            session_id="session-1",
            status="active",
            risk_level="low",
            current_risk_score=0.1,
            detection_count=0,
            total_messages=0,
            messages=[],
        )

        report = build_pdf("Usage summary", [conversation])

        self.assertTrue(report.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
