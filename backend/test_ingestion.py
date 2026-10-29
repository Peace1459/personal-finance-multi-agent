from backend.ingestion.file_loader import load_financial_file
from backend.ingestion.column_detector import detect_columns
from backend.ingestion.normalizer import normalize_transactions


FILE_PATH = "data/sample_transactions.csv"


def main() -> None:
    print("\n==============================")
    print("FINANCEAI INGESTION TEST")
    print("==============================")

    print("\n1. Loading file...")

    dataframe = load_financial_file(FILE_PATH)

    print("File loaded successfully.")

    print("\n2. Raw columns:")
    print(dataframe.columns.tolist())

    print("\n3. Detecting columns...")

    detected_columns = detect_columns(dataframe.columns)

    print("Detected columns:")
    print(detected_columns)

    print("\n4. Normalizing transactions...")

    result = normalize_transactions(
        dataframe,
        detected_columns,
    )

    print("Normalization completed.")

    print("\n5. Normalized transactions:")

    if result.transactions.empty:
        print("No valid transactions found.")
    else:
        print(result.transactions.to_string(index=False))

    print("\n6. Import issues:")

    if result.issues:
        for issue in result.issues:
            print(
                f"Row {issue.row_number}: "
                f"[{issue.issue_type}] "
                f"{issue.message}"
            )
    else:
        print("No issues found.")



    print("\n7. Potential duplicates:")

    if result.duplicates:
        for duplicate in result.duplicates:
          print(
            f"Transactions {duplicate.transaction_indices}: "
            f"{duplicate.reason}"
        )
    else:
        print("No potential duplicates found.")




    income = result.transactions.loc[
        result.transactions["amount"] > 0,
        "amount",
    ].sum()

    expenses = abs(
        result.transactions.loc[
            result.transactions["amount"] < 0,
            "amount",
        ].sum()
    )

    remaining = income - expenses

    print("\n==============================")
    print("FINANCIAL TOTALS")
    print("==============================")

    print(f"Valid transactions: {result.total_rows}")
    print(f"Import issues:      {result.issue_count}")
    print(f"Rows requiring review: {result.affected_row_count}")
    print(f"Potential duplicate groups: {result.duplicate_count}")
    print(f"Rows involved in duplicates: {result.duplicate_row_count}")
    print(f"Income:             {income:,.2f}")
    print(f"Expenses:           {expenses:,.2f}")
    print(f"Remaining:          {remaining:,.2f}")

    print("\n==============================")
    print("TEST COMPLETE")
    print("==============================")


if __name__ == "__main__":
    main()
