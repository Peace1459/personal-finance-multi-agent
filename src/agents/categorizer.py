from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    timeout=30,
    max_retries=2
)

CATEGORIZER_PROMPT = """
You are the Transaction Categorizer.

Your job is to classify financial transactions into categories.

Use categories such as:
- Income
- Housing
- Food
- Transport
- Utilities
- Entertainment
- Shopping
- Healthcare
- Other

Do not calculate a budget.
Do not provide investment advice.
Do not invent transactions.

For each transaction, provide:
- description
- amount
- category
"""


def categorizer_agent(state):
    transactions = state["transactions"]

    prompt = f"""
{CATEGORIZER_PROMPT}

Transactions:

{transactions}
"""

    response = llm.invoke(prompt)

    return {
        "categorized_transactions": response.content
    }

