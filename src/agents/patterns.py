from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    timeout=30,
    max_retries=2
)


def pattern_agent(state):
    transactions = state.get("categorized_transactions", [])

    income = state.get("income", 0)
    expenses = state.get("expenses", 0)
    remaining = state.get("remaining", 0)

    prompt = f"""
You are the Spending Pattern Detector in a Personal Finance Assistant.

Analyze the categorized transactions below.

IMPORTANT:
The Python calculation tool has already calculated the authoritative
financial totals:

Income: {income}
Expenses: {expenses}
Remaining: {remaining}

You MUST NOT recalculate, change, or contradict these totals.

Categorized transactions:

{transactions}

Identify:

1. Large spending categories.
2. Frequent expenses.
3. Recurring expenses.
4. Potentially discretionary spending.
5. Unusual observations.

Rules:

- Use only information present in the transactions.
- Do not invent transactions or amounts.
- Do not change the authoritative income, expenses, or remaining values.
- Clearly distinguish observations from assumptions.
- Do not create a budget.
- Do not provide investment advice.

If you mention total expenses or remaining income, use exactly:

Expenses: {expenses}
Remaining: {remaining}
"""

    response = llm.invoke(prompt)

    return {
        "spending_patterns": [response.content]
    }
