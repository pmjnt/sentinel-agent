from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.chat import (
    ActionType,
    AnalyzePortfolioAction,
    ParsedRequest,
    UpdatePolicyAction,
)


def test_combined_update_and_analyze_actions_keep_their_order() -> None:
    request = ParsedRequest.model_validate(
        {
            "actions": [
                {
                    "type": "UPDATE_POLICY",
                    "patch": {"max_asset_weight": "0.40"},
                },
                {
                    "type": "ANALYZE_PORTFOLIO",
                    "focus_symbols": [" btc "],
                },
            ]
        }
    )

    assert isinstance(request.actions[0], UpdatePolicyAction)
    assert request.actions[0].patch.max_asset_weight == Decimal("0.40")
    assert isinstance(request.actions[1], AnalyzePortfolioAction)
    assert request.actions[1].focus_symbols == ["BTC"]


def test_empty_action_list_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ParsedRequest(actions=[])


def test_view_action_rejects_policy_patch_data() -> None:
    with pytest.raises(ValidationError):
        ParsedRequest.model_validate(
            {
                "actions": [
                    {
                        "type": ActionType.VIEW_POLICY.value,
                        "patch": {"max_asset_weight": "0.40"},
                    }
                ]
            }
        )


def test_blank_clarification_question_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ParsedRequest.model_validate(
            {
                "actions": [
                    {
                        "type": ActionType.NEEDS_CLARIFICATION.value,
                        "question": "   ",
                    }
                ]
            }
        )
