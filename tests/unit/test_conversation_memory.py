from app.agent.conversation_memory import (
    ConversationSessionStore,
    filter_conversation_history,
)


def test_session_store_reuses_session_per_user_and_isolates_users() -> None:
    store = ConversationSessionStore()

    first = store.get("user-1")

    assert store.get("user-1") is first
    assert store.get("user-2") is not first


def test_history_filter_keeps_recent_conversation_but_removes_tool_data() -> None:
    history = [
        {
            "role": "user",
            "content": (
                "Current validated portfolio policy:\n{}\n\n"
                "User message:\nGive me investment advice."
            ),
        },
        {
            "type": "function_call",
            "name": "get_portfolio",
            "arguments": "{}",
            "call_id": "call-1",
        },
        {
            "type": "function_call_output",
            "call_id": "call-1",
            "output": '{"total_usd_value":"9999.00"}',
        },
        {
            "role": "assistant",
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": "Would you prefer safety or growth?",
                }
            ],
        },
    ]
    new_input = [
        {
            "role": "user",
            "content": (
                "Current validated portfolio policy:\n{}\n\n"
                "User message:\nMore growth."
            ),
        }
    ]

    result = filter_conversation_history(history, new_input)

    assert len(result) == 3
    assert result[0]["content"] == "Give me investment advice."
    assert result[1]["role"] == "assistant"
    assert result[2] == new_input[0]
    assert all(item.get("type") != "function_call_output" for item in result)


def test_history_filter_keeps_only_sixteen_recent_conversation_messages() -> None:
    history = [
        {"role": "user", "content": f"message-{index}"}
        for index in range(20)
    ]
    new_input = [{"role": "user", "content": "current"}]

    result = filter_conversation_history(history, new_input)

    assert [item["content"] for item in result[:-1]] == [
        f"message-{index}" for index in range(4, 20)
    ]
    assert result[-1] == new_input[0]
