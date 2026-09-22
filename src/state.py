from typing import TypedDict


class FinanceState(TypedDict, total=False):
    user_query: str
    transactions: list
    categorized_transactions: list

    income: float
    expenses: float
    remaining: float

    budget: dict
    spending_patterns: list
    savings_scenarios: list

    critique: str
    approved: bool

    revision_count: int

    human_approved: bool | None
    human_feedback: str

    interface: str

    final_response: str
    