
from pydantic import BaseModel
from typing import Literal

class ImportIssueResponse(BaseModel):
    row_number: int
    issue_type: str
    message: str
    source_row_id: int | None = None


class DuplicateGroupResponse(BaseModel):
    transaction_indices: list[int]
    source_row_ids: list[int]
    reason: str


class ImportResponse(BaseModel):
    import_id: str
    total_rows: int
    imported_rows: int
    issue_count: int
    duplicate_group_count: int
    duplicate_row_count: int
    transactions: list[dict]
    issues: list[ImportIssueResponse]
    duplicates: list[DuplicateGroupResponse]

class FinancialSummaryResponse(BaseModel):
    transaction_count: int
    income: float
    expenses: float
    remaining_balance: float


class ReviewSummaryResponse(BaseModel):
    total_rows: int
    imported_rows: int
    import_issue_count: int
    rows_with_import_issues: int
    duplicate_group_count: int
    rows_in_duplicate_groups: int
    category_review_count: int
    total_rows_requiring_review: int


class FinancialSummaryResponse(BaseModel):
    transaction_count: int
    income: float
    expenses: float
    remaining_balance: float

class ReviewSummaryResponse(BaseModel):
    total_rows: int
    imported_rows: int
    import_issue_count: int
    rows_with_import_issues: int
    duplicate_group_count: int
    rows_in_duplicate_groups: int
    category_review_count: int
    total_rows_requiring_review: int


class CrossImportTransactionResponse(BaseModel):
    id: int
    import_id: str
    source_row_id: int
    transaction_date: str
    description: str
    amount: float
    transaction_type: str
    merchant: str | None
    category: str
    needs_review: bool


class CrossImportDuplicateResponse(BaseModel):
    id: int
    new_transaction: CrossImportTransactionResponse
    existing_transaction: CrossImportTransactionResponse
    reason: str
    status: str
    created_at: str


class CrossImportDuplicatesResponse(BaseModel):
    count: int
    duplicates: list[CrossImportDuplicateResponse]


class CrossImportDuplicateReviewRequest(BaseModel):
    status: Literal["confirmed", "dismissed"]



class CrossImportDuplicateStatusResponse(BaseModel):
    id: int
    status: Literal["pending", "confirmed", "dismissed"]
