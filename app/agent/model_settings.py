from agents import ModelSettings
from openai.types.shared.reasoning import Reasoning

from app.config import LLMProvider, Settings


def build_agent_model_settings(settings: Settings) -> ModelSettings:
    """Build explicit SDK settings for the selected LiteLLM provider route."""
    reasoning = None
    if (
        settings.llm_provider is LLMProvider.OPENAI
        and settings.llm_model.lower().startswith("gpt-5")
    ):
        reasoning = Reasoning(effort="none")

    return ModelSettings(
        max_tokens=settings.llm_max_tokens,
        parallel_tool_calls=False,
        reasoning=reasoning,
    )
