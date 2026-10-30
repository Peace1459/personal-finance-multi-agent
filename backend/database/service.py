
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.orm import aliased
from backend.database.models import (
    CrossImportDuplicate,
    DuplicateGroupRecord,
    ImportBatch,
    ImportIssueRecord,
    Transaction,
)
from backend.ingestion.cross_import_detector import (
    detect_cross_import_duplicates,
)

def get_import_by_file_hash(session: Session, file_hash: str):
    """Return an existing import batch with the same file hash, if any."""

    statement = select(ImportBatch).where(
        ImportBatch.file_hash == file_hash
    )
    return session.execute(statement).scalar_one_or_none()

def get_import_batches(session: Session):
    """Return all import batches, newest first."""

    statement = select(ImportBatch).order_by(
        ImportBatch.created_at.desc()
    )
    return session.execute(statement).scalars().all()


def save_import_result(
    session: Session,
    result,
    file_hash: str | None = None,
) -> tuple[str, int]:
    """Save an import batch and all its records atomically."""

    import_id = str(uuid4())
    transactions = result.transactions
    review = result.review_summary()

    batch = ImportBatch(
        id=import_id,
        file_hash=file_hash,
        total_rows=result.total_rows,
        imported_rows=len(transactions),
        issue_count=result.issue_count,
        affected_row_count=result.affected_row_count,
        duplicate_group_count=result.duplicate_count,
        duplicate_row_count=result.duplicate_row_count,
        category_review_count=review.category_review_count,
        total_rows_requiring_review=review.total_rows_requiring_review,
    )

    # Read previously saved transactions before adding this import.
    existing_records = session.scalars(
        select(Transaction)
    ).all()

    existing_transactions = pd.DataFrame(
        [
            {
                "id": record.id,
                "import_id": record.import_id,
                "transaction_date": record.transaction_date,
                "description": record.description,
                "amount": record.amount,
            }
            for record in existing_records
        ],
        columns=[
            "id",
            "import_id",
            "transaction_date",
            "description",
            "amount",
        ],
    )

    transaction_records = []

    for _, row in transactions.iterrows():
        source_row_id = row.get("source_row_id")
        amount = row["amount"]

        if pd.isna(source_row_id):
            raise ValueError("A transaction is missing its source row ID.")

        if pd.isna(amount):
            raise ValueError("A transaction has an invalid amount.")

        transaction_records.append(
            Transaction(
                import_id=import_id,
                source_row_id=int(source_row_id),
                transaction_date=pd.to_datetime(
                    row["transaction_date"]
                ).date(),
                description=str(row["description"]),
                amount=float(amount),
                transaction_type=str(row["transaction_type"]),
                merchant=(
                    str(row["merchant"])
                    if pd.notna(row.get("merchant"))
                    else None
                ),
                category=str(row["category"]),
                needs_review=bool(row["needs_review"]),
            )
        )

    issue_records = [
        ImportIssueRecord(
            import_id=import_id,
            row_number=issue.row_number,
            source_row_id=issue.source_row_id,
            issue_type=issue.issue_type,
            message=issue.message,
        )
        for issue in result.issues
    ]

    duplicate_records = [
        DuplicateGroupRecord(
            import_id=import_id,
            reason=group.reason,
            source_row_ids=list(group.source_row_ids),
            transaction_indices=list(group.transaction_indices),
        )
        for group in result.duplicates
    ]

    try:
        session.add(batch)
        session.add_all(transaction_records)
        session.add_all(issue_records)
        session.add_all(duplicate_records)

        # Obtain database IDs without committing the import.
        session.flush()

        # Match the new normalized transactions against earlier imports.
        matches = detect_cross_import_duplicates(
            transactions,
            existing_transactions,
        )

        cross_import_records = []

        for match in matches:
            new_transaction = transaction_records[
                match.new_transaction_index
            ]

            cross_import_records.append(
                CrossImportDuplicate(
                    new_transaction_id=new_transaction.id,
                    existing_transaction_id=match.existing_transaction_id,
                    reason=match.reason,
                    status="pending",
                )
            )

        session.add_all(cross_import_records)
        session.commit()

    except Exception:
        session.rollback()
        raise

    return import_id, len(transaction_records)



def save_transactions(
    session: Session,
    transactions: pd.DataFrame,
) -> tuple[str, int]:
    """Save transactions only; retained for existing callers."""

    import_id = str(uuid4())
    records = []

    for _, row in transactions.iterrows():
        source_row_id = row.get("source_row_id")
        amount = row["amount"]

        if pd.isna(source_row_id):
            raise ValueError("A transaction is missing its source row ID.")

        if pd.isna(amount):
            raise ValueError("A transaction has an invalid amount.")

        records.append(
            Transaction(
                import_id=import_id,
                source_row_id=int(source_row_id),
                transaction_date=pd.to_datetime(
                    row["transaction_date"]
                ).date(),
                description=str(row["description"]),
                amount=float(amount),
                transaction_type=str(row["transaction_type"]),
                merchant=(
                    str(row["merchant"])
                    if pd.notna(row.get("merchant"))
                    else None
                ),
                category=str(row["category"]),
                needs_review=bool(row["needs_review"]),
            )
        )

    try:
        session.add_all(records)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return import_id, len(records)


def get_transactions(
    session: Session,
    import_id: str | None = None,
) -> list[Transaction]:
    query = session.query(Transaction)

    if import_id is not None:
        query = query.filter(Transaction.import_id == import_id)

    return query.order_by(
        Transaction.transaction_date.desc(),
        Transaction.id.desc(),
    ).all()


def get_financial_summary(
    session: Session,
    import_id: str | None = None,
) -> dict:
    transactions = get_transactions(session, import_id)

    income = sum(
        transaction.amount
        for transaction in transactions
        if transaction.amount > 0
    )
    expenses = sum(
        -transaction.amount
        for transaction in transactions
        if transaction.amount < 0
    )

    return {
        "transaction_count": len(transactions),
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "remaining_balance": round(income - expenses, 2),
    }

def get_review_summary(
    session: Session,
    import_id: str | None = None,
) -> dict:
    """Retrieve persisted review counts for one or all imports."""

    query = session.query(ImportBatch)

    if import_id is not None:
        query = query.filter(ImportBatch.id == import_id)

    batches = query.all()

    return {
        "total_rows": sum(batch.total_rows for batch in batches),
        "imported_rows": sum(batch.imported_rows for batch in batches),
        "import_issue_count": sum(
            batch.issue_count for batch in batches
        ),
        "rows_with_import_issues": sum(
            batch.affected_row_count for batch in batches
        ),
        "duplicate_group_count": sum(
            batch.duplicate_group_count for batch in batches
        ),
        "rows_in_duplicate_groups": sum(
            batch.duplicate_row_count for batch in batches
        ),
        "category_review_count": sum(
            batch.category_review_count for batch in batches
        ),
        "total_rows_requiring_review": sum(
            batch.total_rows_requiring_review for batch in batches
        ),
    }


def get_cross_import_duplicates(
    session: Session,
    status: str | None = None,
) -> list[dict]:
    """Retrieve suspected duplicates and the details of both transactions."""

    ExistingTransaction = aliased(Transaction)

    query = (
        session.query(
            CrossImportDuplicate,
            Transaction,
            ExistingTransaction,
        )
        .join(
            Transaction,
            CrossImportDuplicate.new_transaction_id == Transaction.id,
        )
        .join(
            ExistingTransaction,
            CrossImportDuplicate.existing_transaction_id
            == ExistingTransaction.id,
        )
    )

    if status is not None:
        query = query.filter(CrossImportDuplicate.status == status)

    records = query.order_by(CrossImportDuplicate.id.desc()).all()

    def transaction_to_dict(transaction: Transaction) -> dict:
        return {
            "id": transaction.id,
            "import_id": transaction.import_id,
            "source_row_id": transaction.source_row_id,
            "transaction_date": transaction.transaction_date.isoformat(),
            "description": transaction.description,
            "amount": transaction.amount,
            "transaction_type": transaction.transaction_type,
            "merchant": transaction.merchant,
            "category": transaction.category,
            "needs_review": transaction.needs_review,
        }

    return [
        {
            "id": duplicate.id,
            "new_transaction": transaction_to_dict(new_transaction),
            "existing_transaction": transaction_to_dict(existing_transaction),
            "reason": duplicate.reason,
            "status": duplicate.status,
            "created_at": duplicate.created_at.isoformat(),
        }
        for duplicate, new_transaction, existing_transaction in records
    ]


def update_cross_import_duplicate_status(
    session: Session,
    duplicate_id: int,
    status: str,
):
   if status not in {"confirmed", "dismissed"}:
        raise ValueError(
            "Status must be 'confirmed' or 'dismissed'."
        )
   duplicate = session.get(CrossImportDuplicate, duplicate_id)

   if duplicate is None:
        return None
   duplicate.status = status
   try:
        session.commit()
   except Exception:
        session.rollback()
        raise
   return duplicate
