
from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class ImportIssue:
    row_number: int
    issue_type: str
    message: str
    source_row_id: int | None = None


@dataclass(frozen=True)
class DuplicateGroup:
    transaction_indices: tuple[int, ...]
    reason: str
    source_row_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ReviewSummary:
    import_issue_count: int
    rows_with_import_issues: int
    duplicate_group_count: int
    rows_in_duplicate_groups: int
    category_review_count: int
    review_flag_count: int
    total_rows_requiring_review: int


@dataclass
class ImportResult:
    transactions: pd.DataFrame
    issues: list[ImportIssue] = field(default_factory=list)
    duplicates: list[DuplicateGroup] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return len(self.transactions)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def affected_row_count(self) -> int:
        return len({
            issue.source_row_id
            if issue.source_row_id is not None
            else issue.row_number
            for issue in self.issues
        })

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicates)

    @property
    def duplicate_row_count(self) -> int:
        source_ids = {
            source_id
            for group in self.duplicates
            for source_id in group.source_row_ids
        }

        if source_ids:
            return len(source_ids)

        return len({
            index
            for group in self.duplicates
            for index in group.transaction_indices
        })

    def review_summary(self) -> ReviewSummary:
        issue_rows = {
            issue.source_row_id
            for issue in self.issues
            if issue.source_row_id is not None
        }

        # Fallback for older issue objects without source IDs.
        issue_rows.update(
            ("legacy_issue", issue.row_number)
            for issue in self.issues
            if issue.source_row_id is None
        )

        duplicate_rows = {
            source_id
            for group in self.duplicates
            for source_id in group.source_row_ids
        }

        if not duplicate_rows:
            duplicate_rows = {
                ("legacy_duplicate", index)
                for group in self.duplicates
                for index in group.transaction_indices
            }

        category_review_rows = set()

        if "source_row_id" in self.transactions.columns:
            source_ids = self.transactions["source_row_id"]
        else:
            source_ids = pd.Series(
                self.transactions.index,
                index=self.transactions.index,
            )

        needs_review = pd.Series(
            False,
            index=self.transactions.index,
        )

        if "needs_review" in self.transactions.columns:
            needs_review |= (
                self.transactions["needs_review"]
                .fillna(True)
                .astype(bool)
            )

        if "category" in self.transactions.columns:
            needs_review |= (
                self.transactions["category"]
                .fillna("Uncategorized")
                .eq("Uncategorized")
            )

        category_review_rows.update(
            source_ids.loc[needs_review].tolist()
        )

        # Use tagged tuples to prevent a fallback index from colliding
        # with a source ID. Source IDs are stable across pipeline stages.
        all_reviewed_rows = (
            {("source", value) for value in issue_rows}
            | {("source", value) for value in duplicate_rows}
            | {("source", value) for value in category_review_rows}
        )

        # Count review conditions separately; one row may have several.
        review_flag_count = (
            len(self.issues)
            + len(self.duplicates)
            + len(category_review_rows)
        )

        return ReviewSummary(
            import_issue_count=len(self.issues),
            rows_with_import_issues=len(issue_rows),
            duplicate_group_count=len(self.duplicates),
            rows_in_duplicate_groups=len(duplicate_rows),
            category_review_count=len(category_review_rows),
            review_flag_count=review_flag_count,
            total_rows_requiring_review=len(all_reviewed_rows),
        )
