from typing import TypedDict, Any
class AgentState(TypedDict, total=False):
    message: str
    email: str
    session_id: str
    requirements: dict
    steps: int
    trajectory: list[dict]
    status: str
    stop_reason: str
    offers: list[dict]
    comparison: list[dict]
    budget_result: dict
    proposal: dict
    order: dict
    email_result: dict
    total_tokens: int
    estimated_cost: float | None
    explanation: str
