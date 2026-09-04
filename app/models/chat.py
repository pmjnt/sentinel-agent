from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.policy import PolicyPatch


class ActionType(str, Enum):
    UPDATE_POLICY = "UPDATE_POLICY"
    VIEW_POLICY = "VIEW_POLICY"
    ANALYZE_PORTFOLIO = "ANALYZE_PORTFOLIO"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class UpdatePolicyAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal[ActionType.UPDATE_POLICY] = ActionType.UPDATE_POLICY
    patch: PolicyPatch


class ViewPolicyAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal[ActionType.VIEW_POLICY] = ActionType.VIEW_POLICY


class AnalyzePortfolioAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal[ActionType.ANALYZE_PORTFOLIO] = ActionType.ANALYZE_PORTFOLIO
    focus_symbols: list[str] = Field(default_factory=list)

    @field_validator("focus_symbols")
    @classmethod
    def normalize_focus_symbols(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Focus symbols must not be empty.")
        return normalized


class ClarificationAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal[ActionType.NEEDS_CLARIFICATION] = (
        ActionType.NEEDS_CLARIFICATION
    )
    question: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("Clarification question must not be empty.")
        return question


RequestedAction = Annotated[
    UpdatePolicyAction
    | ViewPolicyAction
    | AnalyzePortfolioAction
    | ClarificationAction,
    Field(discriminator="type"),
]


class ParsedRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actions: list[RequestedAction] = Field(min_length=1)
