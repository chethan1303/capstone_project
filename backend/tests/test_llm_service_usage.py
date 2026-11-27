import unittest
from unittest.mock import patch

from services.llm_service import LLMService, MockLLMService


class _FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class _FakeAsyncClient:
    def __init__(self, response, **kwargs):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def post(self, *args, **kwargs):
        return self.response


class LLMServiceUsageTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_service_returns_provider_token_usage(self):
        response = _FakeResponse({
            "choices": [{"message": {"content": "Answer"}}],
            "usage": {"prompt_tokens": 23, "completion_tokens": 8},
        })
        with patch(
            "services.llm_service.httpx.AsyncClient",
            return_value=_FakeAsyncClient(response),
        ):
            result = await LLMService().generate_response("system", [])

        self.assertEqual(result.content, "Answer")
        self.assertEqual(result.prompt_tokens, 23)
        self.assertEqual(result.completion_tokens, 8)

    async def test_missing_or_invalid_usage_is_reported_as_unavailable(self):
        response = _FakeResponse({
            "choices": [{"message": {"content": "Answer"}}],
            "usage": {"prompt_tokens": 23, "completion_tokens": "8"},
        })
        with patch(
            "services.llm_service.httpx.AsyncClient",
            return_value=_FakeAsyncClient(response),
        ):
            result = await LLMService().generate_response("system", [])

        self.assertEqual(result.prompt_tokens, 23)
        self.assertIsNone(result.completion_tokens)

    async def test_mock_service_reports_zero_provider_tokens(self):
        result = await MockLLMService().generate_response("system", [])

        self.assertEqual(result.prompt_tokens, 0)
        self.assertEqual(result.completion_tokens, 0)


if __name__ == "__main__":
    unittest.main()
