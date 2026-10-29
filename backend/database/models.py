

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from backend.database.connection import Base



class Transaction(Base):
    """Persisted financial transaction."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    import_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
    )

    source_row_id: Mapped[int] = mapped_column(Integer)

    transaction_date: Mapped[date] = mapped_column(Date)

    description: Mapped[str] = mapped_column(String(1000))

    amount: Mapped[float] = mapped_column(Float)

    transaction_type: Mapped[str] = mapped_column(String(20))

    merchant: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        default="Uncategorized",
    )

    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )


class ImportBatch(Base):
    """Stores metadata and review counts for one CSV import."""

    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    file_hash: Mapped[str | None] = mapped_column(
       String(64),
       nullable=True,
       unique=True,
)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    issue_count: Mapped[int] = mapped_column(Integer, default=0)
    affected_row_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_group_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_row_count: Mapped[int] = mapped_column(Integer, default=0)
    category_review_count: Mapped[int] = mapped_column(Integer, default=0)
    total_rows_requiring_review: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ImportIssueRecord(Base):
    """Stores an issue detected while processing an imported CSV."""

    __tablename__ = "import_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_id: Mapped[str] = mapped_column(
        ForeignKey("import_batches.id"),
        index=True,
    )
    row_number: Mapped[int] = mapped_column(Integer)
    source_row_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    issue_type: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(String(2000))


class DuplicateGroupRecord(Base):
    """Stores a detected duplicate group for one CSV import."""

    __tablename__ = "duplicate_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_id: Mapped[str] = mapped_column(
        ForeignKey("import_batches.id"),
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(500))
    source_row_ids: Mapped[list[int]] = mapped_column(JSON)
    transaction_indices: Mapped[list[int]] = mapped_column(JSON)


class CrossImportDuplicate(Base):
    """Stores a suspected duplicate between two imported transactions."""

    __tablename__ = "cross_import_duplicates"

    __table_args__ = (
        UniqueConstraint(
            "new_transaction_id",
            "existing_transaction_id",
            name="uq_cross_import_duplicate_pair",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    new_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=False,
        index=True,
    )

    existing_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
