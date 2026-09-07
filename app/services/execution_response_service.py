from app.models.execution import ExecutionPlan


def format_pending_execution_plan(plan: ExecutionPlan) -> str:
    approval = (
        "token exception approval, then Demo order approval"
        if plan.requires_symbol_override
        else "required for every Demo order"
    )
    return "\n".join(
        [
            "Pending Binance Demo plan:",
            f"- Plan ID: {plan.plan_id}",
            f"- Action: {plan.side.value} {plan.symbol}",
            f"- Value: ${plan.quote_usd:,.2f}",
            f"- Estimated quantity: {plan.estimated_quantity}",
            f"- Reason: {plan.reason}",
            f"- Approval: {approval}",
            "- Execution: NOT_EXECUTED — No order has been sent.",
        ]
    )
