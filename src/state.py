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
    human_approved: bool
    human_feedback: str
    revision_count: int
    final_response: str
