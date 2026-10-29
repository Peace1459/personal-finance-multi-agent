
from backend.ingestion.file_loader import load_financial_file
from backend.ingestion.column_detector import detect_columns
from backend.ingestion.normalizer import normalize_transactions


FILE_PATH = "data/test_unknown_category.csv"


def main() -> None:
    raw_transactions = load_financial_file(FILE_PATH)
    column_mapping = detect_columns(raw_transactions.columns)

    result = normalize_transactions(
        raw_transactions,
        column_mapping,
    )

    transactions = result.transactions

    unknown_rows = transactions.loc[
        transactions["description"] == "Unknown Store 123"
    ]

    # The unfamiliar transaction must be retained.
    assert len(unknown_rows) == 1, (
        "Unknown transaction was missing or duplicated."
    )

    unknown = unknown_rows.iloc[0]

    # It must remain uncategorized and require review.
    assert unknown["category"] == "Uncategorized", (
        f"Unexpected category: {unknown['category']!r}"
    )

    assert bool(unknown["needs_review"]) is True, (
        "Unknown transaction was not flagged for review."
    )

    # The original description and amount must be preserved.
    assert unknown["description"] == "Unknown Store 123"
    assert unknown["amount"] == -2500

    # All three transactions should remain in the result.
    assert len(transactions) == 3

    # The financial totals must remain correct.
    income = transactions.loc[
        transactions["amount"] > 0, "amount"
    ].sum()

    expenses = abs(
        transactions.loc[
            transactions["amount"] < 0, "amount"
        ].sum()
    )

    remaining = income - expenses

    assert income == 120000, f"Unexpected income: {income}"
    assert expenses == 32500, f"Unexpected expenses: {expenses}"
    assert remaining == 87500, f"Unexpected remaining: {remaining}"

    print("\nUNKNOWN CATEGORY INTEGRATION TEST")
    print("=================================")
    print("PASS: Unknown transaction retained")
    print("PASS: Category is Uncategorized")
    print("PASS: needs_review is True")
    print("PASS: Original description and amount preserved")
    print("PASS: All three transactions retained")
    print(f"PASS: Income = {income:,.2f}")
    print(f"PASS: Expenses = {expenses:,.2f}")
    print(f"PASS: Remaining = {remaining:,.2f}")
    print("\nAll integration assertions passed.")


if __name__ == "__main__":
    main()
