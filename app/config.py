import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    openai_api_key: str


def load_settings() -> Settings:
    """Load local environment variables and validate required configuration."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your key."
        )

    return Settings(openai_api_key=api_key)
