from app.models.execution import ExecutionPlan


def format_pending_execution_plan(plan: ExecutionPlan) -> str:
    return "\n".join(
        [
            "Pending Binance Demo plan:",
            f"- Plan ID: {plan.plan_id}",
            f"- Action: {plan.side.value} {plan.symbol}",
            f"- Value: ${plan.quote_usd:,.2f}",
            f"- Estimated quantity: {plan.estimated_quantity}",
            f"- Reason: {plan.reason}",
            "- Approval: required for every Demo order",
            "- Execution: NOT_EXECUTED — No order has been sent.",
        ]
    )
