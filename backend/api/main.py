import hashlib
from datetime import date
from io import BytesIO

import pandas as pd
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.schemas import (
    CrossImportDuplicateReviewRequest,
    CrossImportDuplicatesResponse,
    CrossImportDuplicateStatusResponse,
    DuplicateGroupResponse,
    FinancialSummaryResponse,
    ImportIssueResponse,
    ImportResponse,
    ReviewSummaryResponse,
    TransactionUpdateRequest,
)
from backend.api.summary_service import calculate_financial_summary
from backend.database.connection import SessionLocal
from backend.database.models import Transaction
from backend.database.service import (
    get_financial_summary,
    get_import_batches,
    get_import_by_file_hash,
    get_review_summary,
    get_transaction_categories,
    get_transactions,
    get_cross_import_duplicates,
    save_import_result,
    save_transactions,
    update_cross_import_duplicate_status,
    update_transaction,
)
from backend.ingestion.column_detector import detect_columns
from backend.ingestion.normalizer import normalize_transactions

app = FastAPI(
    title="FinanceAI API",
    description="Backend API for personal finance transaction analysis.",
    version="0.1.0",
)
MAX_CSV_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors = []

    for error in exc.errors():
        safe_error = error.copy()

        # Remove raw input values because they may contain NaN or Infinity,
        # which are not valid JSON values.
        safe_error.pop("input", None)
        safe_error.pop("ctx", None)

        errors.append(safe_error)

    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )

@app.middleware("http")
async def limit_upload_size(request, call_next):
    if request.url.path == "/transactions/import":
        content_length = request.headers.get("content-length")

        if content_length is not None:
            try:
                request_size = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header."},
                )

            if request_size > MAX_CSV_UPLOAD_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "The request exceeds the 5 MB size limit."},
                )

    return await call_next(request)

@app.get("/health")
def health_check() -> dict[str, str]:
    """Confirm that the API server is running."""
    return {
        "status": "ok",
        "service": "FinanceAI API",
    }



@app.post("/transactions/import", response_model=ImportResponse)
async def import_transactions(
    file: UploadFile = File(...),
) -> ImportResponse:
    """Import transactions from a CSV file."""

    result, file_hash = await _normalize_uploaded_csv(file)
    db: Session = SessionLocal()

    try:
        existing_import = get_import_by_file_hash(db, file_hash)

        if existing_import is not None:
          raise HTTPException(
            status_code=409,
            detail=(
                "This CSV file has already been imported. "
                f"Existing import ID: {existing_import.id}"
            ),
        )

        import_id, saved_count = save_import_result(
           db,
           result,
           file_hash=file_hash,
    )

    except IntegrityError as exc:
      db.rollback()

      existing_import = get_import_by_file_hash(db, file_hash)

      if existing_import is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "This CSV file has already been imported. "
                f"Existing import ID: {existing_import.id}"
            ),
        ) from exc

      raise

    finally:
     db.close()

    transactions = result.transactions.copy()

    if "transaction_date" in transactions.columns:
        transactions["transaction_date"] = (
            transactions["transaction_date"].astype(str)
        )

    transactions = transactions.astype(object).where(
        pd.notna(transactions),
        None,
    )

    transaction_records = transactions.to_dict(orient="records")

    issues = [
        ImportIssueResponse(
            row_number=issue.row_number,
            issue_type=issue.issue_type,
            message=issue.message,
            source_row_id=getattr(issue, "source_row_id", None),
        )
        for issue in result.issues
    ]

    duplicates = [
        DuplicateGroupResponse(
            transaction_indices=list(group.transaction_indices),
            source_row_ids=list(
                getattr(group, "source_row_ids", ())
            ),
            reason=group.reason,
        )
        for group in result.duplicates
        ]
    return ImportResponse(
       import_id=import_id,
       total_rows=result.total_rows,
       imported_rows=len(result.transactions),
       issue_count=result.issue_count,
       duplicate_group_count=result.duplicate_count,
       duplicate_row_count=result.duplicate_row_count,
       transactions=transaction_records,
       issues=issues,
       duplicates=duplicates,
)



async def _normalize_uploaded_csv(file: UploadFile):
    """Read and normalize an uploaded CSV file."""

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    try:
        file_bytes = await file.read(MAX_CSV_UPLOAD_SIZE + 1)
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        if len(file_bytes) > MAX_CSV_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="The uploaded CSV exceeds the 5 MB size limit.",
            )
        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        dataframe = pd.read_csv(BytesIO(file_bytes))

        if dataframe.empty:
            raise HTTPException(
                status_code=400,
                detail="The CSV file contains no transaction rows.",
            )

        if len(dataframe.columns) > 100:
            raise HTTPException(
                status_code=400,
                detail="The CSV contains too many columns.",
            )

        detected_columns = detect_columns(dataframe.columns)

        result = normalize_transactions(dataframe, detected_columns)
        return result, file_hash

    except HTTPException:
        raise

    except (UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not read the CSV file. Check its encoding and format.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    finally:
        await file.close()

@app.post("/summary", response_model=FinancialSummaryResponse)
async def financial_summary(
    file: UploadFile = File(...),
) -> FinancialSummaryResponse:
    """Calculate financial totals from an uploaded CSV."""

    result = await _normalize_uploaded_csv(file)

    summary = calculate_financial_summary(result.transactions)

    return FinancialSummaryResponse(**summary)

@app.post("/review-summary", response_model=ReviewSummaryResponse)
async def review_summary(
    file: UploadFile = File(...),
) -> ReviewSummaryResponse:
    """Summarize rows requiring review after CSV import."""

    result = await _normalize_uploaded_csv(file)
    transactions = result.transactions

    # Identify rows with import issues.
    issue_row_ids = {
        getattr(issue, "source_row_id", None)
        for issue in result.issues
    }
    issue_row_ids.discard(None)

    # Fall back to source row numbers for older issue records.
    issue_row_ids.update(
        issue.row_number - 2
        for issue in result.issues
        if getattr(issue, "source_row_id", None) is None
    )

    # Identify all rows belonging to duplicate groups.
    duplicate_row_ids = set()

    for group in result.duplicates:
        source_ids = getattr(group, "source_row_ids", ())

        if source_ids:
            duplicate_row_ids.update(source_ids)
        else:
            for index in group.transaction_indices:
                if 0 <= index < len(transactions):
                    if "source_row_id" in transactions.columns:
                        duplicate_row_ids.add(
                            int(transactions.iloc[index]["source_row_id"])
                        )
                    else:
                        duplicate_row_ids.add(index)

    # Identify transactions whose categories need review.
    category_row_ids = set()

    if "needs_review" in transactions.columns:
        needs_review = (
            transactions["needs_review"]
            .fillna(False)
            .astype(bool)
        )

        if "source_row_id" in transactions.columns:
            category_row_ids.update(
                transactions.loc[needs_review, "source_row_id"]
                .dropna()
                .astype(int)
            )
        else:
            category_row_ids.update(
                transactions.index[needs_review]
            )

    # A row flagged for multiple reasons counts only once.
    all_review_row_ids = (
        issue_row_ids
        | duplicate_row_ids
        | category_row_ids
    )

    # Invalid rows are excluded from normalized transactions.
    # Count unique invalid source rows, not individual issue records.
    invalid_row_ids = {
        getattr(issue, "source_row_id", None)
        for issue in result.issues
    }
    invalid_row_ids.discard(None)

    invalid_row_ids.update(
        issue.row_number - 2
        for issue in result.issues
        if getattr(issue, "source_row_id", None) is None
    )

    total_rows = len(transactions) + len(invalid_row_ids)

    return ReviewSummaryResponse(
        total_rows=total_rows,
        imported_rows=len(transactions),
        import_issue_count=result.issue_count,
        rows_with_import_issues=result.affected_row_count,
        duplicate_group_count=result.duplicate_count,
        rows_in_duplicate_groups=result.duplicate_row_count,
        category_review_count=len(category_row_ids),
        total_rows_requiring_review=len(all_review_row_ids),
    )

@app.get("/imports")
def list_imports() -> dict:
    """Retrieve saved CSV import history."""

    db = SessionLocal()

    try:
        batches = get_import_batches(db)

        return {
            "count": len(batches),
            "imports": [
                {
                    "id": batch.id,
                    "created_at": batch.created_at.isoformat(),
                    "total_rows": batch.total_rows,
                    "imported_rows": batch.imported_rows,
                    "issue_count": batch.issue_count,
                    "affected_row_count": batch.affected_row_count,
                    "duplicate_group_count": batch.duplicate_group_count,
                    "duplicate_row_count": batch.duplicate_row_count,
                    "category_review_count": batch.category_review_count,
                    "total_rows_requiring_review": (
                        batch.total_rows_requiring_review
                    ),
                }
                for batch in batches
            ],
        }

    finally:
        db.close()




@app.get("/transactions")
def list_transactions(
    import_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    transaction_type: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> dict:
    """Retrieve saved transactions using optional filters."""

    db = SessionLocal()

    try:
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date cannot be after end_date.",
            )

        transactions = get_transactions(
            db,
            import_id=import_id,
            search=search,
            category=category,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "count": len(transactions),
            "transactions": [
                {
                    "id": transaction.id,
                    "import_id": transaction.import_id,
                    "source_row_id": transaction.source_row_id,
                    "transaction_date": (
                        transaction.transaction_date.isoformat()
                    ),
                    "description": transaction.description,
                    "amount": transaction.amount,
                    "transaction_type": transaction.transaction_type,
                    "merchant": transaction.merchant,
                    "category": transaction.category,
                    "needs_review": transaction.needs_review,
                }
                for transaction in transactions
            ],
        }

    finally:
        db.close()

@app.patch("/transactions/{transaction_id}")
def edit_transaction(
    transaction_id: int,
    payload: TransactionUpdateRequest,
) -> dict:
    """Update an existing transaction."""

    db = SessionLocal()

    try:
        existing_transaction = db.get(Transaction, transaction_id)

        if existing_transaction is None:
            raise HTTPException(
                status_code=404,
                detail="Transaction not found.",
            )
        updates = payload.model_dump(exclude_unset=True)

        # Required transaction fields cannot be set to null.
        required_fields = {
            "transaction_date",
            "description",
            "amount",
            "transaction_type",
            "category",
        }

        for field in required_fields:
            if field in updates and updates[field] is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"{field} cannot be null.",
                )
        final_amount = updates.get("amount", existing_transaction.amount)

        final_type = updates.get(
            "transaction_type",
            existing_transaction.transaction_type,
        )

        if final_amount == 0:
            raise HTTPException(
                status_code=422,
                detail="Transaction amount cannot be zero.",
            )

        if final_type == "income" and final_amount < 0:
            raise HTTPException(
                status_code=422,
                detail="Income transactions must have a positive amount.",
            )

        if final_type == "expense" and final_amount > 0:
            raise HTTPException(
                status_code=422,
                detail="Expense transactions must have a negative amount.",
            )

        if "description" in updates:
            updates["description"] = updates["description"].strip()

        if "category" in updates:
            updates["category"] = updates["category"].strip()

        if "merchant" in updates and updates["merchant"] is not None:
            updates["merchant"] = updates["merchant"].strip() or None

        transaction = update_transaction(
            db,
            transaction_id,
            updates,
        )

        if transaction is None:
            raise HTTPException(
                status_code=404,
                detail="Transaction not found.",
            )

        return {
            "message": "Transaction updated successfully.",
            "transaction": {
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
            },
        }

    finally:
        db.close()


@app.get("/transaction-categories")
def list_transaction_categories() -> dict:
    """Retrieve distinct transaction categories."""

    db = SessionLocal()

    try:
        categories = get_transaction_categories(db)

        return {
            "count": len(categories),
            "categories": categories,
        }

    finally:
        db.close()

@app.get("/summary", response_model=FinancialSummaryResponse)
def saved_financial_summary(
    import_id: str | None = Query(default=None),
) -> FinancialSummaryResponse:
    """Calculate financial totals from saved transactions."""

    db = SessionLocal()

    try:
        summary = get_financial_summary(db, import_id)
        return FinancialSummaryResponse(**summary)
    finally:
        db.close()

@app.get(
    "/review-summary",
    response_model=ReviewSummaryResponse,
)
def review_summary(
    import_id: str | None = Query(default=None),
) -> ReviewSummaryResponse:
    """Return persisted review counts for imported transactions."""

    db: Session = SessionLocal()

    try:
        summary = get_review_summary(db, import_id)
        return ReviewSummaryResponse(**summary)
    finally:
        db.close()


@app.get(
    "/cross-import-duplicates",
    response_model=CrossImportDuplicatesResponse,
)
def list_cross_import_duplicates(
    status: str | None = Query(
        default=None,
        description="Optionally filter by status, such as pending.",
    ),
):
    db = SessionLocal()

    try:
        duplicates = get_cross_import_duplicates(db, status=status)

        return {
            "count": len(duplicates),
            "duplicates": duplicates,
        }
    finally:
        db.close()


@app.patch(
    "/cross-import-duplicates/{duplicate_id}",
    response_model=CrossImportDuplicateStatusResponse,
)
def review_cross_import_duplicate(
    duplicate_id: int,
    review: CrossImportDuplicateReviewRequest,
):
    db = SessionLocal()
    try:
        duplicate = update_cross_import_duplicate_status(
            db,
            duplicate_id=duplicate_id,
            status=review.status,
        )

        if duplicate is None:
            raise HTTPException(
                status_code=404,
                detail="Cross-import duplicate not found.",
            )

        return {
            "id": duplicate.id,
            "status": duplicate.status,
        }
    finally:
        db.close()
