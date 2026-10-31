from datetime import date
from math import isfinite
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal


class ImportIssueResponse(BaseModel):
    row_number: int
    issue_type: str
    message: str
    source_row_id: int | None = None


class TransactionUpdateRequest(BaseModel):
    """Validate updates to an existing transaction."""

    model_config = ConfigDict(extra="forbid")

    transaction_date: date | None = None
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    amount: float | None = None
    transaction_type: Literal["income", "expense"] | None = None
    merchant: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        if self.description is not None:
            if not self.description.strip():
                raise ValueError("Description cannot be empty.")

        if self.category is not None:
            if not self.category.strip():
                raise ValueError("Category cannot be empty.")

        if self.amount is not None:
            if not isfinite(self.amount):
                raise ValueError("Transaction amount must be finite.")

            if self.amount == 0:
                raise ValueError("Transaction amount cannot be zero.")
        return self

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
