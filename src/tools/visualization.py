import matplotlib.pyplot as plt
from collections import defaultdict


def categorize_for_visualization(transactions):
    """
    Apply simple rule-based categories for visualization.
    This is separate from the AI Categorizer agent.
    """

    category_keywords = {
        "Housing": ["rent", "apartment"],
        "Food": ["supermarket", "restaurant", "food"],
        "Transport": ["uber", "transport"],
        "Entertainment": ["netflix", "entertainment"],
        "Utilities": ["power", "internet", "electricity"],
        "Shopping": ["clothing", "shopping", "mall"],
        "Healthcare": ["hospital", "pharmacy", "medical"],
    }

    categorized = []

    for transaction in transactions:
        description = str(
            transaction.get("description", "")
        ).lower()

        amount = transaction.get("amount", 0)

        category = "Other"

        for possible_category, keywords in category_keywords.items():
            if any(keyword in description for keyword in keywords):
                category = possible_category
                break

        categorized.append({
            "description": transaction.get("description"),
            "amount": amount,
            "category": category,
        })

    return categorized


def create_spending_chart(transactions, output_path):
    """
    Create a bar chart showing spending by category.
    """

    categorized = categorize_for_visualization(transactions)

    spending_by_category = defaultdict(float)

    for transaction in categorized:
        amount = transaction["amount"]

        if amount < 0:
            category = transaction["category"]
            spending_by_category[category] += abs(amount)

    categories = list(spending_by_category.keys())
    amounts = list(spending_by_category.values())

    plt.figure(figsize=(10, 6))

    plt.bar(categories, amounts)

    plt.title("Spending by Category")
    plt.xlabel("Category")
    plt.ylabel("Amount")

    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig(output_path)
    plt.close()

    return output_path
