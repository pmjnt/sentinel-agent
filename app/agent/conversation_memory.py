from typing import cast

from agents import SQLiteSession
from agents.items import TResponseInputItem


MAX_CONVERSATION_MESSAGES = 16
_USER_MESSAGE_MARKER = "\n\nUser message:\n"


class ConversationSessionStore:
    """Own one process-local Agents SDK conversation session per user."""

    def __init__(self) -> None:
        self._sessions: dict[str, SQLiteSession] = {}

    def get(self, session_id: str) -> SQLiteSession:
        normalized = session_id.strip()
        if not normalized:
            raise ValueError("Session ID must not be empty.")
        if normalized not in self._sessions:
            self._sessions[normalized] = SQLiteSession(normalized)
        return self._sessions[normalized]


def filter_conversation_history(
    history: list[TResponseInputItem],
    new_input: list[TResponseInputItem],
) -> list[TResponseInputItem]:
    """Keep short conversational history without replaying old tool data."""
    messages: list[TResponseInputItem] = []
    for item in history:
        if not isinstance(item, dict) or item.get("role") not in {
            "user",
            "assistant",
        }:
            continue

        copied = dict(item)
        if copied.get("role") == "user" and isinstance(
            copied.get("content"), str
        ):
            copied["content"] = _original_user_message(copied["content"])
        messages.append(cast(TResponseInputItem, copied))

    return messages[-MAX_CONVERSATION_MESSAGES:] + list(new_input)


def _original_user_message(content: str) -> str:
    if _USER_MESSAGE_MARKER not in content:
        return content
    return content.rsplit(_USER_MESSAGE_MARKER, maxsplit=1)[1]
