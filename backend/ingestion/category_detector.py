
from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryResult:
    category: str
    needs_review: bool


def _normalize_text(value: str | None) -> str:
    """Normalize text for deterministic category matching."""
    if not isinstance(value, str):
        return ""

    return " ".join(value.strip().lower().split())


# Explicit rules for descriptions that identify a category.
DESCRIPTION_CATEGORIES = {
    "salary": "Income",
    "apartment rent": "Housing",
    "restaurant": "Dining",
    "clothing store": "Shopping",
    "shopping mall": "Shopping",
    "internet": "Internet & Phone",
}

# Explicit rules for recognized merchants.
MERCHANT_CATEGORIES = {
    "naivas supermarket": "Groceries",
    "uber": "Transport",
    "netflix": "Subscriptions",
    "kenya power": "Utilities",
}


def detect_category(
    description: str,
    merchant: str | None = None,
) -> CategoryResult:
    """
    Assign a category using explicit description and merchant rules.

    Unknown transactions remain Uncategorized and require review.
    The original description is never modified.
    """
    normalized_description = _normalize_text(description)

    # Prefer an exact description rule when one exists.
    category = DESCRIPTION_CATEGORIES.get(normalized_description)

    if category is not None:
        return CategoryResult(
            category=category,
            needs_review=False,
        )

    # Otherwise, use a recognized merchant.
    normalized_merchant = _normalize_text(merchant)
    category = MERCHANT_CATEGORIES.get(normalized_merchant)

    if category is not None:
        return CategoryResult(
            category=category,
            needs_review=False,
        )

    return CategoryResult(
        category="Uncategorized",
        needs_review=True,
    )
