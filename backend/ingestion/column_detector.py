COLUMN_ALIASES = {
    "transaction_date": {
        "date",
        "transaction date",
        "transaction_date",
        "posted date",
        "posted_date",
        "value date",
        "value_date",
    },
    "description": {
        "description",
        "details",
        "narration",
        "transaction details",
        "transaction_details",
        "merchant",
        "reference",
    },
    "amount": {
        "amount",
        "transaction amount",
        "transaction_amount",
    },
    "debit": {
        "debit",
        "withdrawal",
        "withdrawals",
        "debits",
    },
    "credit": {
        "credit",
        "deposit",
        "deposits",
        "credits",
    },
}


def normalize_column_name(column_name: str) -> str:
    """
    Convert a raw column name into a standard comparison format.
    """

    return " ".join(
        str(column_name).strip().lower().split()
    )


def detect_columns(columns) -> dict:
    """
    Map uploaded file columns to FinanceAI's canonical fields.

    Raises:
        ValueError: If multiple uploaded columns map to the same
        canonical field.
    """

    detected = {}
    conflicts = {}

    for column in columns:
        normalized = normalize_column_name(column)

        matches = [
            canonical_name
            for canonical_name, aliases in COLUMN_ALIASES.items()
            if normalized in aliases
        ]

        if len(matches) == 1:
            canonical_name = matches[0]

            if canonical_name in detected:
                conflicts.setdefault(canonical_name, []).append(column)
            else:
                detected[canonical_name] = column

    if conflicts:
        conflict_messages = []

        for canonical_name, columns_found in conflicts.items():
            all_columns = [
                detected[canonical_name],
                *columns_found,
            ]

            conflict_messages.append(
                f"{canonical_name}: {all_columns}"
            )

        raise ValueError(
            "Ambiguous column mapping detected. "
            "Multiple uploaded columns match the same FinanceAI field: "
            + "; ".join(conflict_messages)
        )

    return detected
