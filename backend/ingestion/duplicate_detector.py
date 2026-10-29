
import pandas as pd

from backend.ingestion.models import DuplicateGroup


def _normalize_description(description: str) -> str:
    """Normalize a description for duplicate comparison."""
    return " ".join(
        str(description).strip().lower().split()
    )


def detect_duplicates(
    transactions: pd.DataFrame,
) -> list[DuplicateGroup]:
    """
    Group potential duplicates by date, signed amount,
    and normalized description.

    Transactions are flagged, never deleted.
    """
    required_columns = {
        "transaction_date",
        "description",
        "amount",
    }

    missing_columns = required_columns - set(transactions.columns)

    if missing_columns:
        raise ValueError(
            "Duplicate detection requires these columns: "
            + ", ".join(sorted(missing_columns))
        )

    if transactions.empty:
        return []

    comparison = transactions.copy()

    comparison["normalized_description"] = (
        comparison["description"].map(_normalize_description)
    )

    signature_columns = [
        "transaction_date",
        "amount",
        "normalized_description",
    ]

    duplicate_mask = comparison.duplicated(
        subset=signature_columns,
        keep=False,
    )

    duplicate_rows = comparison.loc[duplicate_mask]

    groups = []

    for _, group in duplicate_rows.groupby(
        signature_columns,
        sort=False,
        dropna=False,
    ):
        if len(group) < 2:
            continue

        transaction_indices = tuple(
            int(index) for index in group.index
        )

        if "source_row_id" in group.columns:
            source_row_ids = tuple(
                int(source_id)
                for source_id in group["source_row_id"]
            )
        else:
            # Backward compatibility for callers that have not yet
            # adopted source_row_id.
            source_row_ids = ()

        groups.append(
            DuplicateGroup(
                transaction_indices=transaction_indices,
                reason=(
                    "Same transaction date, amount, "
                    "and normalized description."
                ),
                source_row_ids=source_row_ids,
            )
        )

    return groups
