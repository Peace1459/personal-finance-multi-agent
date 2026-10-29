
MERCHANT_ALIASES = {
    "uber": "Uber",
    "uber trip": "Uber",
    "uber *trip": "Uber",
    "naivas": "Naivas Supermarket",
    "naivas supermarket": "Naivas Supermarket",
    "netflix": "Netflix",
    "kenya power": "Kenya Power",
    "kplc": "Kenya Power",
}


def _normalize_text(value: str) -> str:
    """Standardize text for merchant alias lookup."""
    return " ".join(
        str(value).strip().lower().split()
    )


def normalize_merchant(description: str) -> str | None:
    """
    Return a recognized merchant name.

    Unknown descriptions return None rather than being guessed.
    The original description is never modified.
    """
    if not isinstance(description, str) or not description.strip():
        return None

    normalized_description = _normalize_text(description)

    return MERCHANT_ALIASES.get(normalized_description)
