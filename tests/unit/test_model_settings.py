from app.agent.model_settings import build_agent_model_settings
from app.config import LLMProvider, Settings


def test_openai_gpt54_omits_redundant_reasoning_effort_for_litellm_tools() -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-5.4-mini",
        openai_api_key="test-key",
        llm_max_tokens=4096,
    )

    model_settings = build_agent_model_settings(settings)

    assert model_settings.max_tokens == 4096
    assert model_settings.reasoning is None
    assert model_settings.parallel_tool_calls is False


def test_gemini_omits_openai_reasoning_setting() -> None:
    settings = Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.5-flash-lite",
        gemini_api_key="test-key",
        llm_max_tokens=2048,
    )

    model_settings = build_agent_model_settings(settings)

    assert model_settings.max_tokens == 2048
    assert model_settings.reasoning is None
    assert model_settings.parallel_tool_calls is False
