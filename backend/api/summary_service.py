
import pandas as pd


def calculate_financial_summary(
    transactions: pd.DataFrame,
) -> dict:
    """Calculate financial totals from normalized transactions."""

    amounts = pd.to_numeric(
        transactions["amount"],
        errors="raise",
    )

    income = amounts[amounts > 0].sum()
    expenses = -amounts[amounts < 0].sum()

    return {
        "transaction_count": len(transactions),
        "income": round(float(income), 2),
        "expenses": round(float(expenses), 2),
        "remaining_balance": round(float(income - expenses), 2),
    }
