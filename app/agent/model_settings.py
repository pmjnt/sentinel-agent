from agents import ModelSettings

from app.config import Settings


def build_agent_model_settings(settings: Settings) -> ModelSettings:
    """Build explicit SDK settings for the selected LiteLLM provider route."""
    return ModelSettings(
        max_tokens=settings.llm_max_tokens,
        parallel_tool_calls=False,
    )
