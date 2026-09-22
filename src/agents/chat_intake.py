import re


def chat_intake_agent(user_query):
    """
    Extract simple financial transactions from natural-language chat.

    Income is positive.
    Expenses are negative.
    """

    text = user_query.lower()

    transactions = []

    # --------------------------------------------------
    # Income
    # --------------------------------------------------

    income_patterns = [
        r"(?:monthly income|monthly salary|salary|income|earn)\D{0,30}(\d+(?:,\d{3})*(?:\.\d+)?)"
    ]

    for pattern in income_patterns:

        match = re.search(pattern, text)

        if match:

            amount = float(
                match.group(1).replace(",", "")
            )

            transactions.append(
                {
                    "description": "Income",
                    "amount": amount,
                }
            )

            break

    # --------------------------------------------------
    # Expense categories
    # --------------------------------------------------

    expense_categories = {
        "rent": [
            "rent",
            "house rent",
            "apartment rent",
        ],
        "food": [
            "food",
            "groceries",
            "groceries",
        ],
        "transport": [
            "transport",
            "transportation",
            "uber",
            "travel",
        ],
        "entertainment": [
            "entertainment",
            "netflix",
            "movies",
        ],
        "utilities": [
            "utilities",
            "electricity",
            "power",
            "internet",
            "water",
        ],
        "shopping": [
            "shopping",
            "clothes",
            "clothing",
        ],
        "healthcare": [
            "healthcare",
            "health",
            "hospital",
            "medical",
            "medicine",
        ],
    }

    for category, keywords in expense_categories.items():

        for keyword in keywords:

            pattern = (
                rf"{re.escape(keyword)}"
                rf"\D{{0,30}}"
                rf"(\d+(?:,\d{{3}})*(?:\.\d+)?)"
            )

            match = re.search(pattern, text)

            if match:

                amount = float(
                    match.group(1).replace(",", "")
                )

                transactions.append(
                    {
                        "description": category.title(),
                        "amount": -amount,
                    }
                )

                break

    return transactions
