
import unittest

import pandas as pd

from backend.ingestion.cross_import_detector import (
    detect_cross_import_duplicates,
)


class TestCrossImportDetector(unittest.TestCase):
    def test_detects_exact_match_and_preserves_original_index(self):
        new = pd.DataFrame(
            {
                "transaction_date": ["2026-10-01"],
                "description": ["  NAIVAS   Supermarket "],
                "amount": [-8500.0],
            },
            index=[7],
        )

        existing = pd.DataFrame(
            {
                "id": [42],
                "import_id": ["previous-import"],
                "transaction_date": ["2026-10-01"],
                "description": ["Naivas Supermarket"],
                "amount": [-8500.0],
            }
        )

        matches = detect_cross_import_duplicates(new, existing)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].new_transaction_index, 7)
        self.assertEqual(matches[0].existing_transaction_id, 42)

    def test_different_amount_does_not_match(self):
        new = pd.DataFrame(
            {
                "transaction_date": ["2026-10-01"],
                "description": ["Naivas Supermarket"],
                "amount": [-8500.0],
            }
        )

        existing = pd.DataFrame(
            {
                "id": [42],
                "import_id": ["previous-import"],
                "transaction_date": ["2026-10-01"],
                "description": ["Naivas Supermarket"],
                "amount": [-9000.0],
            }
        )

        self.assertEqual(
            detect_cross_import_duplicates(new, existing),
            [],
        )

    def test_empty_input_returns_no_matches(self):
        new = pd.DataFrame(
            columns=["transaction_date", "description", "amount"]
        )
        existing = pd.DataFrame(
            columns=[
                "id",
                "import_id",
                "transaction_date",
                "description",
                "amount",
            ]
        )

        self.assertEqual(
            detect_cross_import_duplicates(new, existing),
            [],
        )


if __name__ == "__main__":
    unittest.main()
