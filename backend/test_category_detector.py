
from backend.ingestion.category_detector import detect_category


def main() -> None:
    test_cases = [
        ("Salary", None, "Income", False),
        ("Apartment Rent", None, "Housing", False),
        ("Naivas Supermarket", "Naivas Supermarket", "Groceries", False),
        ("Uber", "Uber", "Transport", False),
        ("Netflix", "Netflix", "Subscriptions", False),
        ("Kenya Power", "Kenya Power", "Utilities", False),
        ("Restaurant", None, "Dining", False),
        ("Clothing Store", None, "Shopping", False),
        ("Internet", None, "Internet & Phone", False),
        ("Unknown Store 123", None, "Uncategorized", True),
        ("", None, "Uncategorized", True),
    ]

    failures = []

    print("\nCATEGORY DETECTOR TEST")
    print("======================")

    for description, merchant, expected_category, expected_review in test_cases:
        result = detect_category(description, merchant)

        passed = (
            result.category == expected_category
            and result.needs_review == expected_review
        )

        status = "PASS" if passed else "FAIL"

        print(
            f"{status}: {description!r} -> "
            f"{result.category!r}, "
            f"needs_review={result.needs_review}"
        )

        if not passed:
            failures.append(
                f"{description!r}: expected "
                f"({expected_category!r}, {expected_review}), got "
                f"({result.category!r}, {result.needs_review})"
            )

    if failures:
        raise AssertionError("\n".join(failures))

    print("\nAll category tests passed.")


if __name__ == "__main__":
    main()
