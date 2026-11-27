"""
PI-EWS LLM Service.

Integrates with Groq's OpenAI-compatible chat completion API.
Includes a mock service for testing without an API key.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

from config import settings


@dataclass(frozen=True)
class LLMResult:
    content: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


def _read_token_count(usage: object, key: str) -> Optional[int]:
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


class LLMService:
    """Calls the configured OpenAI-compatible chat completion API."""

    async def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        defense_additions: Optional[str] = None,
    ) -> LLMResult:
        """Generate a response from the Gemini API.

        Args:
            system_prompt: The honeypot persona prompt.
            conversation_history: List of {"role": ..., "content": ...} dicts.
            defense_additions: Extra system instructions from the defense engine.

        Returns:
            The model response and provider-reported token usage.
        """
        # Build combined system instruction
        full_system = system_prompt
        if defense_additions:
            full_system += "\n\n" + defense_additions

        messages = [{"role": "system", "content": full_system}]
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["content"]})

        payload = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_completion_tokens": 1024,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    settings.LLM_API_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                choices = data.get("choices", [])
                usage = data.get("usage")
                prompt_tokens = _read_token_count(usage, "prompt_tokens")
                completion_tokens = _read_token_count(usage, "completion_tokens")
                if choices:
                    content = choices[0].get("message", {}).get("content")
                    if content:
                        return LLMResult(
                            content=content,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                        )

                return LLMResult(
                    content="I'm having trouble responding right now. Please try again.",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

        except httpx.HTTPStatusError as e:
            print(f"LLM API error: {e.response.status_code} — {e.response.text}")
            return LLMResult(
                content="I apologize, I'm experiencing technical difficulties. Please try again shortly."
            )
        except Exception as e:
            print(f"LLM service error: {e}")
            return LLMResult(
                content="I apologize, I'm experiencing technical difficulties. Please try again shortly."
            )


class MockLLMService:
    """Mock LLM for testing without an API key.

    Returns plausible honeypot-style canned responses.
    """

    _RESPONSES = [
        "Of course! I'd be happy to help with that. Let me pull up the relevant "
        "information from our internal systems. What specific project are you working on?",

        "I can certainly look into that for you. Could you provide your employee ID "
        "so I can access the right records?",

        "Great question! According to our internal documentation, that information "
        "is available through the project management portal. Would you like me to "
        "guide you through accessing it?",

        "I'd be glad to assist! For security purposes, could you verify your "
        "department and team lead? Then I can provide the details you need.",

        "Sure thing! Let me check our systems. While I do that, is there anything "
        "else you need help with today?",

        "I understand your request. That falls under our IT support procedures. "
        "Let me create a ticket for you. Can you describe the issue in more detail?",
    ]

    def __init__(self):
        self._index = 0

    async def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        defense_additions: Optional[str] = None,
    ) -> LLMResult:
        response = self._RESPONSES[self._index % len(self._RESPONSES)]
        self._index += 1
        return LLMResult(content=response, prompt_tokens=0, completion_tokens=0)


def get_llm_service() -> LLMService | MockLLMService:
    """Factory: return the real service if an API key is configured, else mock."""
    if settings.LLM_API_KEY and settings.LLM_API_KEY not in {
        "your-groq-api-key",
        "your-gemini-api-key",
    }:
        return LLMService()
    return MockLLMService()
