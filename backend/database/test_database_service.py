
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.connection import Base
from backend.database.models import Transaction
from backend.database.service import (
    get_financial_summary,
    get_transactions,
)

from backend.database.models import (
    DuplicateGroupRecord,
    ImportBatch,
    ImportIssueRecord,
    CrossImportDuplicate,
)
from backend.database.service import (
    get_review_summary,
    save_import_result,
    update_cross_import_duplicate_status,
)
from backend.ingestion.column_detector import detect_columns
from backend.ingestion.normalizer import normalize_transactions


class TestDatabaseService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        database_path = Path(self.temp_dir.name) / "test_financeai.db"

        self.engine = create_engine(
            f"sqlite:///{database_path.as_posix()}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        self.addCleanup(self.engine.dispose)

        Base.metadata.create_all(bind=self.engine)

        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

        self.session = self.SessionLocal()
        self.addCleanup(self.session.close)

        self.session.add_all([
            Transaction(
                import_id="test-import-001",
                source_row_id=1,
                transaction_date=date(2026, 10, 1),
                description="Salary",
                amount=120000.0,
                transaction_type="Income",
                merchant=None,
                category="Income",
                needs_review=False,
            ),
            Transaction(
                import_id="test-import-001",
                source_row_id=2,
                transaction_date=date(2026, 10, 2),
                description="Apartment Rent",
                amount=-30000.0,
                transaction_type="Expense",
                merchant=None,
                category="Housing",
                needs_review=False,
            ),
            Transaction(
                import_id="test-import-002",
                source_row_id=1,
                transaction_date=date(2026, 10, 3),
                description="Unknown Store 123",
                amount=-2500.0,
                transaction_type="Expense",
                merchant=None,
                category="Uncategorized",
                needs_review=True,
            ),
        ])
        self.session.commit()

    def test_get_transactions_filters_by_import_id(self):
        transactions = get_transactions(
            self.session,
            import_id="test-import-001",
        )

        self.assertEqual(len(transactions), 2)
        self.assertTrue(
            all(
                transaction.import_id == "test-import-001"
                for transaction in transactions
            )
        )

    def test_get_transactions_returns_all_imports(self):
        transactions = get_transactions(self.session)

        self.assertEqual(len(transactions), 3)

    def test_financial_summary_for_one_import(self):
        summary = get_financial_summary(
            self.session,
            import_id="test-import-001",
        )

        self.assertEqual(summary["transaction_count"], 2)
        self.assertEqual(summary["income"], 120000.0)
        self.assertEqual(summary["expenses"], 30000.0)
        self.assertEqual(summary["remaining_balance"], 90000.0)

    def test_financial_summary_for_all_imports(self):
        summary = get_financial_summary(self.session)

        self.assertEqual(summary["transaction_count"], 3)
        self.assertEqual(summary["income"], 120000.0)
        self.assertEqual(summary["expenses"], 32500.0)
        self.assertEqual(summary["remaining_balance"], 87500.0)

    def test_uncategorized_transaction_is_preserved(self):
        transactions = get_transactions(
            self.session,
            import_id="test-import-002",
        )

        self.assertEqual(len(transactions), 1)
        self.assertEqual(
            transactions[0].description,
            "Unknown Store 123",
        )
        self.assertEqual(transactions[0].category, "Uncategorized")
        self.assertTrue(transactions[0].needs_review)

    def test_save_import_result_persists_batch_and_transactions(self):
        dataframe = pd.DataFrame({
            "date": ["2026-10-01", "2026-10-02"],
            "description": ["Salary", "Apartment Rent"],
            "amount": [120000, -30000],
        })

        detected_columns = detect_columns(dataframe.columns)
        result = normalize_transactions(dataframe, detected_columns)

        import_id, saved_count = save_import_result(
            self.session,
            result,
        )

        self.assertEqual(saved_count, 2)

        batch = self.session.get(ImportBatch, import_id)
        self.assertIsNotNone(batch)
        self.assertEqual(batch.total_rows, 2)
        self.assertEqual(batch.imported_rows, 2)

        saved_transactions = get_transactions(
            self.session,
            import_id=import_id,
        )
        self.assertEqual(len(saved_transactions), 2)

    def test_review_summary_is_persisted(self):
        dataframe = pd.DataFrame({
            "date": ["2026-10-01", "2026-10-02"],
            "description": ["Salary", "Unknown Store 123"],
            "amount": [120000, -2500],
        })

        detected_columns = detect_columns(dataframe.columns)
        result = normalize_transactions(dataframe, detected_columns)

        import_id, _ = save_import_result(self.session, result)

        summary = get_review_summary(
            self.session,
            import_id=import_id,
        )

        self.assertEqual(summary["total_rows"], 2)
        self.assertEqual(summary["imported_rows"], 2)
        self.assertEqual(summary["category_review_count"], 1)
        self.assertEqual(summary["total_rows_requiring_review"], 1)

    def test_duplicate_groups_are_persisted(self):
        project_root = Path(__file__).resolve().parents[2]
        fixture_path = project_root / "data" / "test_multiple_duplicates.csv"

        dataframe = pd.read_csv(fixture_path)
        detected_columns = detect_columns(dataframe.columns)
        result = normalize_transactions(dataframe, detected_columns)

        import_id, _ = save_import_result(self.session, result)

        saved_groups = (
            self.session.query(DuplicateGroupRecord)
            .filter_by(import_id=import_id)
            .all()
        )

        self.assertGreater(len(result.duplicates), 0)
        self.assertEqual(len(saved_groups), len(result.duplicates))

        for group in saved_groups:
            self.assertTrue(group.source_row_ids)
            self.assertTrue(group.reason)

    def test_failed_import_rolls_back_all_records(self):
        initial_batch_count = self.session.query(ImportBatch).count()
        initial_transaction_count = self.session.query(Transaction).count()
        initial_issue_count = self.session.query(ImportIssueRecord).count()
        initial_duplicate_count = self.session.query(DuplicateGroupRecord).count()
        dataframe = pd.DataFrame({
            "date": ["2026-10-01", "2026-10-02"],
            "description": ["Salary", "Apartment Rent"],
            "amount": [120000, -30000],
        })

        detected_columns = detect_columns(dataframe.columns)
        result = normalize_transactions(dataframe, detected_columns)

        original_commit = self.session.commit

        def fail_commit():
            raise RuntimeError("Simulated database failure")

        self.session.commit = fail_commit

        try:
            with self.assertRaises(RuntimeError):
                save_import_result(self.session, result)
        finally:
            self.session.commit = original_commit

        self.assertEqual(
            self.session.query(ImportBatch).count(),
            initial_batch_count,
        )
        self.assertEqual(
            self.session.query(Transaction).count(),
            initial_transaction_count,
        )
        self.assertEqual(
            self.session.query(ImportIssueRecord).count(),
            initial_issue_count,
        )
        self.assertEqual(
            self.session.query(DuplicateGroupRecord).count(),
            initial_duplicate_count,
        )

    def test_cross_import_duplicate_is_saved(self):
       first_dataframe = pd.DataFrame({
        "date": ["2026-10-01"],
        "description": ["Naivas Supermarket"],
        "amount": [-8500.0],
    })

       first_result = normalize_transactions(
        first_dataframe,
        detect_columns(first_dataframe.columns),
    )

       first_import_id, _ = save_import_result(
        self.session,
        first_result,
    )

       second_dataframe = pd.DataFrame({
        "date": ["2026-10-01"],
        "description": [" NAIVAS   SUPERMARKET "],
        "amount": [-8500.0],
    })

       second_result = normalize_transactions(
        second_dataframe,
        detect_columns(second_dataframe.columns),
    )

       second_import_id, _ = save_import_result(
        self.session,
        second_result,
    )

       matches = (
         self.session.query(CrossImportDuplicate)
         .all()
    )

       self.assertNotEqual(first_import_id, second_import_id)
       self.assertEqual(len(matches), 1)
       self.assertEqual(matches[0].status, "pending")

       new_transaction = self.session.get(
          Transaction,
          matches[0].new_transaction_id,
    )
       existing_transaction = self.session.get(
          Transaction,
          matches[0].existing_transaction_id,
    )

       self.assertEqual(new_transaction.import_id, second_import_id)
       self.assertEqual(existing_transaction.import_id, first_import_id)

    def test_cross_import_match_is_not_duplicated_for_same_pair(self):
      dataframe = pd.DataFrame({
        "date": ["2026-10-01"],
        "description": ["Naivas Supermarket"],
        "amount": [-8500.0],
    })

      detected_columns = detect_columns(dataframe.columns)
      result = normalize_transactions(dataframe, detected_columns)

      save_import_result(self.session, result)
      save_import_result(self.session, result)

      matches = (
        self.session.query(CrossImportDuplicate)
        .all()
    )

      # The second import matches the first; the first import has no
      # earlier transaction to match.
      self.assertEqual(len(matches), 1)


    def test_cross_import_records_roll_back_on_commit_failure(self):
      dataframe = pd.DataFrame({
        "date": ["2026-10-01"],
        "description": ["Naivas Supermarket"],
        "amount": [-8500.0],
    })

      detected_columns = detect_columns(dataframe.columns)
      result = normalize_transactions(dataframe, detected_columns)

      save_import_result(self.session, result)

      initial_batch_count = self.session.query(ImportBatch).count()
      initial_transaction_count = self.session.query(Transaction).count()
      initial_match_count = self.session.query(CrossImportDuplicate).count()

      original_commit = self.session.commit

      def fail_commit():
        raise RuntimeError("Simulated database failure")

      self.session.commit = fail_commit

      try:
        with self.assertRaises(RuntimeError):
            save_import_result(self.session, result)
      finally:
        self.session.commit = original_commit

      self.assertEqual(
        self.session.query(ImportBatch).count(),
        initial_batch_count,
    )
      self.assertEqual(
        self.session.query(Transaction).count(),
        initial_transaction_count,
    )
      self.assertEqual(
        self.session.query(CrossImportDuplicate).count(),
        initial_match_count,
    )


    def test_update_cross_import_duplicate_status_rejects_invalid_status(self):
        with self.assertRaisesRegex(
            ValueError,
            "Status must be 'confirmed' or 'dismissed'.",
        ):
            update_cross_import_duplicate_status(
                self.session,
                duplicate_id=1,
                status="maybe",
            )


if __name__ == "__main__":
    unittest.main()
