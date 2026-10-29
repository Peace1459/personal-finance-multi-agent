
import pandas as pd

from backend.ingestion.category_detector import detect_category
from backend.ingestion.duplicate_detector import detect_duplicates
from backend.ingestion.merchant_normalizer import normalize_merchant
from backend.ingestion.models import ImportIssue, ImportResult


def _parse_amounts(
    dataframe: pd.DataFrame,
    detected_columns: dict,
    source_row_ids: pd.Series,
) -> tuple[pd.Series, list[ImportIssue], set[int]]:
    """
    Normalize amounts to a signed numeric convention.

    Positive amounts represent money entering the account.
    Negative amounts represent money leaving the account.

    Invalid rows are identified using the original DataFrame index.
    Issues retain a stable source_row_id for traceability.
    """
    issues: list[ImportIssue] = []
    invalid_indices: set[int] = set()

    if "amount" in detected_columns:
        amount_column = detected_columns["amount"]

        raw_amounts = dataframe[amount_column]
        amounts = pd.to_numeric(raw_amounts, errors="coerce")

        invalid_amounts = amounts.isna()

        for index in dataframe.index[invalid_amounts]:
            source_id = int(source_row_ids.loc[index])

            issues.append(
                ImportIssue(
                    row_number=source_id + 2,
                    issue_type="invalid_amount",
                    message="Could not interpret the transaction amount.",
                    source_row_id=source_id,
                )
            )
            invalid_indices.add(index)

        return amounts, issues, invalid_indices

    debit = pd.Series(
        0.0,
        index=dataframe.index,
        dtype="float64",
    )
    credit = pd.Series(
        0.0,
        index=dataframe.index,
        dtype="float64",
    )

    if "debit" in detected_columns:
        raw_debit = dataframe[detected_columns["debit"]]
        parsed_debit = pd.to_numeric(raw_debit, errors="coerce")

        invalid_debit = parsed_debit.isna() & raw_debit.notna()

        for index in dataframe.index[invalid_debit]:
            source_id = int(source_row_ids.loc[index])

            issues.append(
                ImportIssue(
                    row_number=source_id + 2,
                    issue_type="invalid_debit",
                    message="Could not interpret the debit value.",
                    source_row_id=source_id,
                )
            )
            invalid_indices.add(index)

        debit = parsed_debit.fillna(0)

    if "credit" in detected_columns:
        raw_credit = dataframe[detected_columns["credit"]]
        parsed_credit = pd.to_numeric(raw_credit, errors="coerce")

        invalid_credit = parsed_credit.isna() & raw_credit.notna()

        for index in dataframe.index[invalid_credit]:
            source_id = int(source_row_ids.loc[index])

            issues.append(
                ImportIssue(
                    row_number=source_id + 2,
                    issue_type="invalid_credit",
                    message="Could not interpret the credit value.",
                    source_row_id=source_id,
                )
            )
            invalid_indices.add(index)

        credit = parsed_credit.fillna(0)

    both_present = (debit != 0) & (credit != 0)

    for index in dataframe.index[both_present]:
        source_id = int(source_row_ids.loc[index])

        issues.append(
            ImportIssue(
                row_number=source_id + 2,
                issue_type="ambiguous_amount",
                message=(
                    "A transaction contains both debit and "
                    "credit values."
                ),
                source_row_id=source_id,
            )
        )
        invalid_indices.add(index)

    amounts = credit - debit

    return amounts, issues, invalid_indices


def normalize_transactions(
    dataframe: pd.DataFrame,
    detected_columns: dict,
) -> ImportResult:
    """
    Convert raw financial data into FinanceAI's canonical format.

    Invalid rows are excluded from transactions but remain traceable
    through their ImportIssue source_row_id values.
    """

    if "transaction_date" not in detected_columns:
        raise ValueError(
            "Could not identify a transaction date column."
        )

    if "description" not in detected_columns:
        raise ValueError(
            "Could not identify a transaction description column."
        )

    has_amount = "amount" in detected_columns
    has_debit_credit = (
        "debit" in detected_columns
        or "credit" in detected_columns
    )

    if not has_amount and not has_debit_credit:
        raise ValueError(
            "Could not identify transaction amounts. "
            "Expected an amount column or debit/credit columns."
        )

    if has_amount and has_debit_credit:
        raise ValueError(
            "Ambiguous amount structure detected. "
            "The file contains both an amount column and "
            "debit/credit columns."
        )

    # Source IDs are zero-based and stable throughout this import.
    # CSV/Excel row numbers include the header, so source ID + 2
    # identifies the corresponding data row in a typical statement.
    source_row_ids = pd.Series(
        range(len(dataframe)),
        index=dataframe.index,
        dtype="int64",
    )

    normalized = pd.DataFrame(index=dataframe.index)
    normalized["source_row_id"] = source_row_ids

    issues: list[ImportIssue] = []
    invalid_indices = set()

    # Dates
    date_column = detected_columns["transaction_date"]

    normalized["transaction_date"] = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
    )

    invalid_dates = normalized["transaction_date"].isna()

    for index in dataframe.index[invalid_dates]:
        source_id = int(source_row_ids.loc[index])

        issues.append(
            ImportIssue(
                row_number=source_id + 2,
                issue_type="invalid_date",
                message="Could not interpret the transaction date.",
                source_row_id=source_id,
            )
        )
        invalid_indices.add(index)

    # Descriptions
    description_column = detected_columns["description"]

    normalized["description"] = (
        dataframe[description_column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    empty_descriptions = normalized["description"].eq("")

    for index in dataframe.index[empty_descriptions]:
        source_id = int(source_row_ids.loc[index])

        issues.append(
            ImportIssue(
                row_number=source_id + 2,
                issue_type="missing_description",
                message="Transaction description is empty.",
                source_row_id=source_id,
            )
        )
        invalid_indices.add(index)

    # Amounts
    amounts, amount_issues, invalid_amount_indices = _parse_amounts(
        dataframe,
        detected_columns,
        source_row_ids,
    )

    normalized["amount"] = amounts
    issues.extend(amount_issues)
    invalid_indices.update(amount_invalid_index
                           for amount_invalid_index in invalid_amount_indices)

    # Transaction type
    normalized["transaction_type"] = normalized["amount"].apply(
        lambda amount: (
            "income"
            if pd.notna(amount) and amount > 0
            else "expense"
            if pd.notna(amount) and amount < 0
            else "other"
        )
    )

    # Keep valid transactions and their source IDs.
    valid_transactions = normalized.loc[
        ~normalized.index.isin(invalid_indices),
        [
            "source_row_id",
            "transaction_date",
            "description",
            "amount",
            "transaction_type",
        ],
    ].copy()

    valid_transactions["transaction_date"] = (
        valid_transactions["transaction_date"].dt.date
    )

    valid_transactions = valid_transactions.reset_index(drop=True)

    # Merchant normalization preserves the original description.
    valid_transactions["merchant"] = (
        valid_transactions["description"].map(normalize_merchant)
    )

    category_results = [
        detect_category(description, merchant)
        for description, merchant in zip(
            valid_transactions["description"],
            valid_transactions["merchant"],
        )
    ]

    valid_transactions["category"] = [
        result.category for result in category_results
    ]

    valid_transactions["needs_review"] = [
        result.needs_review for result in category_results
    ]

    duplicates = detect_duplicates(valid_transactions)

    return ImportResult(
        transactions=valid_transactions,
        issues=issues,
        duplicates=duplicates,
    )
