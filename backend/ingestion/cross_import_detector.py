
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CrossImportMatch:
    """A suspected match between a new and an existing transaction."""

    new_transaction_index: int
    existing_transaction_id: int
    reason: str


def _normalize_description(description: str) -> str:
    """Normalize a description for duplicate comparison."""
    return " ".join(
        str(description).strip().lower().split()
    )


def detect_cross_import_duplicates(
    new_transactions: pd.DataFrame,
    existing_transactions: pd.DataFrame,
) -> list[CrossImportMatch]:
    """
    Find exact potential matches against previously saved transactions.

    The new DataFrame index is preserved in each match. Transactions
    are flagged for review, never deleted.
    """
    required_new = {
        "transaction_date",
        "description",
        "amount",
    }
    required_existing = {
        "id",
        "transaction_date",
        "description",
        "amount",
        "import_id",
    }

    missing_new = required_new - set(new_transactions.columns)
    missing_existing = (
        required_existing - set(existing_transactions.columns)
    )

    if missing_new:
        raise ValueError(
            "New transactions are missing required columns: "
            + ", ".join(sorted(missing_new))
        )

    if missing_existing:
        raise ValueError(
            "Existing transactions are missing required columns: "
            + ", ".join(sorted(missing_existing))
        )

    if new_transactions.empty or existing_transactions.empty:
        return []

    new_data = new_transactions.copy()
    existing_data = existing_transactions.copy()

    # Keep the caller's original index even after merge operations.
    new_data["_new_transaction_index"] = list(new_data.index)

    new_data["_normalized_description"] = (
        new_data["description"].map(_normalize_description)
    )
    existing_data["_normalized_description"] = (
        existing_data["description"].map(_normalize_description)
    )

    new_data["_comparison_date"] = pd.to_datetime(
        new_data["transaction_date"],
        errors="coerce",
    ).dt.date

    existing_data["_comparison_date"] = pd.to_datetime(
        existing_data["transaction_date"],
        errors="coerce",
    ).dt.date

    # Exclude rows whose dates cannot be compared.
    new_data = new_data.loc[
        new_data["_comparison_date"].notna()
    ]
    existing_data = existing_data.loc[
        existing_data["_comparison_date"].notna()
    ]

    # A transaction must match all three criteria exactly.
    matches = new_data.merge(
        existing_data,
        on=[
            "_comparison_date",
            "amount",
            "_normalized_description",
        ],
        how="inner",
        suffixes=("_new", "_existing"),
    )

    results = []
    seen_pairs = set()

    for _, row in matches.iterrows():
        new_index = int(row["_new_transaction_index"])
        existing_id = int(row["id"])
        pair = (new_index, existing_id)

        if pair in seen_pairs:
            continue

        seen_pairs.add(pair)
        results.append(
            CrossImportMatch(
                new_transaction_index=new_index,
                existing_transaction_id=existing_id,
                reason=(
                    "Same transaction date, signed amount, "
                    "and normalized description as a saved transaction."
                ),
            )
        )

    return results
