
from backend.ingestion.merchant_normalizer import normalize_merchant


def main() -> None:
    test_cases = [
        ("UBER", "Uber"),
        ("uber trip", "Uber"),
        ("  Naivas   Supermarket  ", "Naivas Supermarket"),
        ("NETFLIX", "Netflix"),
        ("KPLC", "Kenya Power"),
        ("Unknown Store 123", None),
        ("", None),
    ]

    print("\nMERCHANT NORMALIZATION TEST")
    print("===========================")

    failures = []

    for description, expected in test_cases:
        actual = normalize_merchant(description)

        passed = actual == expected
        status = "PASS" if passed else "FAIL"

        print(
            f"{status}: {description!r} "
            f"-> {actual!r}"
        )

        if not passed:
            failures.append(
                f"{description!r}: expected {expected!r}, "
                f"got {actual!r}"
            )

    if failures:
        raise AssertionError(
            "\n".join(failures)
        )

    print("\nAll merchant tests passed.")


if __name__ == "__main__":
    main()
