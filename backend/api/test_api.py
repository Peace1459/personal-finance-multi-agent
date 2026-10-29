
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api import main as api_main
from backend.database.connection import Base
from backend.database.models import (
    CrossImportDuplicate,
    ImportBatch,
    Transaction,

)

class TestFinanceAIAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        database_path = Path(self.temp_dir.name) / "test_api.db"

        self.engine = create_engine(
            f"sqlite:///{database_path.as_posix()}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(self.engine.dispose)

        Base.metadata.create_all(bind=self.engine)

        self.TestSessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

        self.session_patch = patch(
            "backend.api.main.SessionLocal",
            self.TestSessionLocal,
        )
        self.session_patch.start()
        self.addCleanup(self.session_patch.stop)

        self.client = TestClient(api_main.app)
        self.addCleanup(self.client.close)

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_import_and_retrieve_transactions(self):
        csv_content = (
            "date,description,amount\n"
            "2026-10-01,Salary,120000\n"
            "2026-10-02,Unknown Store 123,-2500\n"
        )

        response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "transactions.csv",
                    csv_content.encode("utf-8"),
                    "text/csv",
                )
            },
        )

        self.assertEqual(response.status_code, 200, response.text)

        import_data = response.json()
        import_id = import_data["import_id"]

        self.assertEqual(import_data["total_rows"], 2)
        self.assertEqual(import_data["imported_rows"], 2)

        transactions_response = self.client.get(
            "/transactions",
            params={"import_id": import_id},
        )

        self.assertEqual(
            transactions_response.status_code,
            200,
            transactions_response.text,
        )

        transactions_data = transactions_response.json()

        self.assertEqual(transactions_data["count"], 2)

        unknown_transaction = next(
            transaction
            for transaction in transactions_data["transactions"]
            if transaction["description"] == "Unknown Store 123"
        )

        self.assertEqual(
            unknown_transaction["category"],
            "Uncategorized",
        )
        self.assertTrue(unknown_transaction["needs_review"])

    def test_import_rejects_oversized_csv(self):
      oversized_content = (
        b"Date,Description,Amount\n"
        + b"2026-01-01,Test transaction,100\n" * 200_000
    )

      self.assertGreater(len(oversized_content), 5 * 1024 * 1024)

      response = self.client.post(
        "/transactions/import",
        files={
            "file": (
                "oversized.csv",
                   oversized_content,
                "text/csv",
            )
        },
    )

      self.assertEqual(response.status_code, 413)
      self.assertIn("5 MB", response.json()["detail"])

      self.assertEqual(response.status_code, 413)
      self.assertIn("5 MB", response.json()["detail"])

    def test_saved_financial_summary(self):
        csv_content = (
            "date,description,amount\n"
            "2026-10-01,Salary,120000\n"
            "2026-10-02,Apartment Rent,-30000\n"
        )

        import_response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "transactions.csv",
                    csv_content.encode("utf-8"),
                    "text/csv",
                )
            },
        )

        self.assertEqual(
            import_response.status_code,
            200,
            import_response.text,
        )

        import_id = import_response.json()["import_id"]

        response = self.client.get(
            "/summary",
            params={"import_id": import_id},
        )

        self.assertEqual(response.status_code, 200, response.text)

        summary = response.json()

        self.assertEqual(summary["transaction_count"], 2)
        self.assertEqual(summary["income"], 120000)
        self.assertEqual(summary["expenses"], 30000)
        self.assertEqual(summary["remaining_balance"], 90000)

    def test_saved_review_summary(self):
        csv_content = (
            "date,description,amount\n"
            "2026-10-01,Salary,120000\n"
            "2026-10-02,Unknown Store 123,-2500\n"
        )

        import_response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "transactions.csv",
                    csv_content.encode("utf-8"),
                    "text/csv",
                )
            },
        )

        self.assertEqual(
            import_response.status_code,
            200,
            import_response.text,
        )

        import_id = import_response.json()["import_id"]

        response = self.client.get(
            "/review-summary",
            params={"import_id": import_id},
        )

        self.assertEqual(response.status_code, 200, response.text)

        summary = response.json()

        self.assertEqual(summary["total_rows"], 2)
        self.assertEqual(summary["imported_rows"], 2)
        self.assertEqual(summary["category_review_count"], 1)
        self.assertEqual(summary["total_rows_requiring_review"], 1)

    def test_rejects_non_csv_upload(self):
        response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "transactions.txt",
                    b"some text",
                    "text/plain",
                )
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Please upload a CSV file.",
        )

    def test_rejects_empty_csv_file(self):
        response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "empty.csv",
                    b"",
                    "text/csv",
                )
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "The uploaded file is empty.",
        )

    def test_rejects_csv_with_headers_but_no_rows(self):
        csv_content = b"date,description,amount\n"

        response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "no_rows.csv",
                    csv_content,
                    "text/csv",
                )
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "The CSV file contains no transaction rows.",
        )

    def test_rejects_csv_with_missing_required_columns(self):
        csv_content = (
            "date,description\n"
            "2026-10-01,Salary\n"
        ).encode("utf-8")

        response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "missing_amount.csv",
                    csv_content,
                    "text/csv",
                )
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_rejects_ambiguous_column_mapping(self):
        csv_content = (
            "date,transaction date,description,amount\n"
            "2026-10-01,2026-10-01,Salary,120000\n"
        ).encode("utf-8")

        response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "ambiguous.csv",
                    csv_content,
                    "text/csv",
                )
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Ambiguous column mapping",
            response.json()["detail"],
        )

    def test_import_rejects_oversized_request_content_length(self):
        response = self.client.post(
         "/transactions/import",
         headers={"Content-Length": str(6 * 1024 * 1024)},
    )

        self.assertEqual(response.status_code, 413)
        self.assertIn("5 MB", response.json()["detail"])

    def test_import_rejects_same_csv_twice(self):
        csv_content = (
           b"Date,Description,Amount\n"
           b"2026-01-01,Salary,50000\n"
    )

        first_response = self.client.post(
           "/transactions/import",
        files={
            "file": (
                "transactions.csv",
                csv_content,
                "text/csv",
            )
        },
    )

        self.assertEqual(first_response.status_code, 200)
        first_import_id = first_response.json()["import_id"]

        second_response = self.client.post(
          "/transactions/import",
        files={
            "file": (
                "transactions.csv",
                csv_content,
                "text/csv",
            )
        },
    )

        self.assertEqual(second_response.status_code, 409)
        self.assertIn(
            first_import_id,
            second_response.json()["detail"],
    )

        with self.TestSessionLocal() as session:
            batches = session.query(ImportBatch).count()
            transactions = session.query(Transaction).count()

        self.assertEqual(batches, 1)
        self.assertEqual(transactions, 1)


    def test_cross_import_duplicates_endpoint_returns_matching_transactions(self):
        first_csv = (
            "date,description,amount\n"
            "2026-10-01,Naivas Supermarket,-850\n"
        )
        second_csv = (
            "date,description,amount\n"
            "2026-10-01,  NAIVAS   SUPERMARKET  ,-850\n"
        )

        first_response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "first.csv",
                    first_csv.encode("utf-8"),
                    "text/csv",
                )
            },
        )
        self.assertEqual(first_response.status_code, 200, first_response.text)

        second_response = self.client.post(
            "/transactions/import",
            files={
                "file": (
                    "second.csv",
                    second_csv.encode("utf-8"),
                    "text/csv",
                )
            },
        )
        self.assertEqual(second_response.status_code, 200, second_response.text)

        response = self.client.get("/cross-import-duplicates")

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["duplicates"]), 1)

        duplicate = data["duplicates"][0]
        self.assertEqual(duplicate["status"], "pending")
        self.assertIn("same transaction date", duplicate["reason"].lower())

        new_transaction = duplicate["new_transaction"]
        existing_transaction = duplicate["existing_transaction"]

        self.assertEqual(new_transaction["description"], "NAIVAS   SUPERMARKET")
        self.assertEqual(existing_transaction["description"], "Naivas Supermarket")
        self.assertEqual(new_transaction["amount"], -850)
        self.assertEqual(existing_transaction["amount"], -850)
        self.assertNotEqual(new_transaction["id"], existing_transaction["id"])
    def test_review_cross_import_duplicate_confirms_candidate(self):
        first_csv = (
            "date,description,amount\n"
            "2026-10-01,Naivas Supermarket,-850\n"
        )
        second_csv = (
            "date,description,amount\n"
            "2026-10-01,NAIVAS SUPERMARKET,-850\n"
        )

        for filename, content in [
            ("first.csv", first_csv),
            ("second.csv", second_csv),
        ]:
            response = self.client.post(
                "/transactions/import",
                files={
                    "file": (
                        filename,
                        content.encode("utf-8"),
                        "text/csv",
                    )
                },
            )
            self.assertEqual(response.status_code, 200, response.text)

        candidates_response = self.client.get(
            "/cross-import-duplicates"
        )
        self.assertEqual(
            candidates_response.status_code,
            200,
            candidates_response.text,
        )

        duplicates = candidates_response.json()["duplicates"]
        self.assertEqual(len(duplicates), 1)
        duplicate_id = duplicates[0]["id"]

        review_response = self.client.patch(
            f"/cross-import-duplicates/{duplicate_id}",
            json={"status": "confirmed"},
        )

        self.assertEqual(
            review_response.status_code,
            200,
            review_response.text,
        )
        self.assertEqual(
            review_response.json(),
            {"id": duplicate_id, "status": "confirmed"},
        )

        confirmed_response = self.client.get(
            "/cross-import-duplicates",
            params={"status": "confirmed"},
        )
        self.assertEqual(confirmed_response.status_code, 200)
        self.assertEqual(confirmed_response.json()["count"], 1)

        pending_response = self.client.get(
            "/cross-import-duplicates",
            params={"status": "pending"},
        )
        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(pending_response.json()["count"], 0)

    def test_review_cross_import_duplicate_dismisses_candidate(self):
        first_csv = (
        "date,description,amount\n"
        "2026-10-01,Naivas Supermarket,-850\n"
        )
        second_csv = (
            "date,description,amount\n"
            "2026-10-01,NAIVAS SUPERMARKET,-850\n"
        )

        for filename, content in [
            ("first.csv", first_csv),
            ("second.csv", second_csv),
        ]:
            response = self.client.post(
                "/transactions/import",
                files={
                    "file": (
                        filename,
                        content.encode("utf-8"),
                        "text/csv",
                    )
                },
            )
            self.assertEqual(response.status_code, 200, response.text)

        candidates_response = self.client.get(
            "/cross-import-duplicates"
        )
        self.assertEqual(candidates_response.status_code, 200)

        duplicates = candidates_response.json()["duplicates"]
        self.assertEqual(len(duplicates), 1)
        duplicate_id = duplicates[0]["id"]

        review_response = self.client.patch(
            f"/cross-import-duplicates/{duplicate_id}",
            json={"status": "dismissed"},
        )

        self.assertEqual(
            review_response.status_code,
            200,
            review_response.text,
        )
        self.assertEqual(
            review_response.json(),
            {"id": duplicate_id, "status": "dismissed"},
        )

        dismissed_response = self.client.get(
            "/cross-import-duplicates",
            params={"status": "dismissed"},
        )
        self.assertEqual(dismissed_response.status_code, 200)
        self.assertEqual(dismissed_response.json()["count"], 1)

        pending_response = self.client.get(
            "/cross-import-duplicates",
            params={"status": "pending"},
        )
        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(pending_response.json()["count"], 0)

    def test_review_cross_import_duplicate_rejects_invalid_status(self):
        response = self.client.patch(
         "/cross-import-duplicates/1",
            json={"status": "maybe"},
        )

        self.assertEqual(response.status_code, 422)


    def test_review_cross_import_duplicate_returns_404_when_not_found(self):
        response = self.client.patch(
         "/cross-import-duplicates/999999",
            json={"status": "confirmed"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Cross-import duplicate not found.",
        )


    def test_review_preserves_both_transactions(self):
        first_csv = (
            "date,description,amount\n"
            "2026-10-01,Naivas Supermarket,-850\n"
        )
        second_csv = (
            "date,description,amount\n"
            "2026-10-01,NAIVAS SUPERMARKET,-850\n"
        )

        for filename, content in [
            ("first.csv", first_csv),
            ("second.csv", second_csv),
        ]:
            response = self.client.post(
                "/transactions/import",
                files={
                    "file": (
                        filename,
                        content.encode("utf-8"),
                        "text/csv",
                    )
                },
            )
            self.assertEqual(response.status_code, 200, response.text)

        with patch.object(
            api_main,
            "SessionLocal",
            wraps=api_main.SessionLocal,
        ) as session_factory:
            db = session_factory()
            try:
                transaction_count_before = db.query(Transaction).count()
                self.assertEqual(transaction_count_before, 2)

                duplicate = db.query(CrossImportDuplicate).one()
                duplicate_id = duplicate.id
            finally:
                db.close()

        review_response = self.client.patch(
            f"/cross-import-duplicates/{duplicate_id}",
            json={"status": "confirmed"},
        )
        self.assertEqual(
            review_response.status_code,
            200,
            review_response.text,
        )

        db = api_main.SessionLocal()
        try:
            transaction_count_after = db.query(Transaction).count()
            self.assertEqual(transaction_count_after, 2)

            transactions = db.query(Transaction).order_by(
                Transaction.id
            ).all()
            self.assertEqual(len(transactions), 2)

            self.assertEqual(
                {transaction.description for transaction in transactions},
                {"Naivas Supermarket", "NAIVAS SUPERMARKET"},
            )

            duplicate = db.get(CrossImportDuplicate, duplicate_id)
            self.assertIsNotNone(duplicate)
            self.assertEqual(duplicate.status, "confirmed")
        finally:
            db.close()





    def test_cross_import_duplicates_endpoint_filters_by_status(self):
        first_csv = (
            "date,description,amount\n"
            "2026-10-01,Naivas Supermarket,-850\n"
        )
        second_csv = (
            "date,description,amount\n"
            "2026-10-01,NAIVAS SUPERMARKET,-850\n"
        )

        for filename, content in [
            ("first.csv", first_csv),
            ("second.csv", second_csv),
        ]:
            response = self.client.post(
                "/transactions/import",
                files={
                    "file": (
                        filename,
                        content.encode("utf-8"),
                        "text/csv",
                    )
                },
            )
            self.assertEqual(response.status_code, 200, response.text)

        pending_response = self.client.get(
            "/cross-import-duplicates",
            params={"status": "pending"},
        )
        self.assertEqual(pending_response.status_code, 200, pending_response.text)
        self.assertEqual(pending_response.json()["count"], 1)

        dismissed_response = self.client.get(
            "/cross-import-duplicates",
            params={"status": "dismissed"},
        )
        self.assertEqual(dismissed_response.status_code, 200, dismissed_response.text)
        self.assertEqual(dismissed_response.json()["count"], 0)

    def test_cross_import_duplicates_endpoint_returns_empty_list_when_none_exist(self):
        response = self.client.get("/cross-import-duplicates")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {"count": 0, "duplicates": []},
        )

if __name__ == "__main__":
    unittest.main()
