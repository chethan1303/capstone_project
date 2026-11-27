"""Derived usage metrics for stored conversation messages."""

from dataclasses import dataclass
from typing import Optional

from models.conversation import Conversation


@dataclass(frozen=True)
class ConversationMetrics:
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    token_usage_complete: bool
    message_text_bytes: int


def calculate_conversation_metrics(
    conversation: Conversation,
) -> ConversationMetrics:
    assistant_messages = [
        message for message in conversation.messages if message.role == "assistant"
    ]
    token_usage_complete = (
        not conversation.messages
        or (
            bool(assistant_messages)
            and all(
                message.prompt_tokens is not None
                and message.completion_tokens is not None
                for message in assistant_messages
            )
        )
    )

    prompt_tokens = None
    completion_tokens = None
    total_tokens = None
    if token_usage_complete:
        prompt_tokens = sum(message.prompt_tokens or 0 for message in assistant_messages)
        completion_tokens = sum(
            message.completion_tokens or 0 for message in assistant_messages
        )
        total_tokens = prompt_tokens + completion_tokens

    return ConversationMetrics(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        token_usage_complete=token_usage_complete,
        message_text_bytes=sum(
            len(message.content.encode("utf-8")) for message in conversation.messages
        ),
    )
