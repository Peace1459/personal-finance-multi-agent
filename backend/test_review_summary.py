
from backend.ingestion.file_loader import load_financial_file
from backend.ingestion.column_detector import detect_columns
from backend.ingestion.normalizer import normalize_transactions


def load_result(file_path: str):
    raw = load_financial_file(file_path)
    mapping = detect_columns(raw.columns)
    return normalize_transactions(raw, mapping)


def main() -> None:
    normal_result = load_result("data/sample_transactions.csv")
    normal_summary = normal_result.review_summary()

    assert normal_summary.import_issue_count == 0
    assert normal_summary.rows_with_import_issues == 0
    assert normal_summary.duplicate_group_count == 0
    assert normal_summary.rows_in_duplicate_groups == 0
    assert normal_summary.category_review_count == 0

    duplicate_result = load_result("data/test_multiple_duplicates.csv")
    duplicate_summary = duplicate_result.review_summary()

    assert duplicate_summary.duplicate_group_count == 1
    assert duplicate_summary.rows_in_duplicate_groups == 3

    unknown_result = load_result("data/test_unknown_category.csv")
    unknown_summary = unknown_result.review_summary()

    assert unknown_summary.category_review_count == 1

    print("\nREVIEW SUMMARY TEST")
    print("===================")
    print("PASS: Clean import has no review flags")
    print("PASS: Triple duplicate group includes three rows")
    print("PASS: Unknown category is counted for review")
    print("\nAll review summary tests passed.")


if __name__ == "__main__":
    main()
