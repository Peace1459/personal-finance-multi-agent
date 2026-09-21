from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    timeout=30,
    max_retries=2
)

def savings_agent(state):
    remaining = state.get("remaining", 0)
    patterns = state.get("spending_patterns", [])

    prompt = f"""
You are the Savings Advisor in a Personal Finance Assistant.

Available monthly amount:
{remaining}

Spending observations:
{patterns}

Create three hypothetical monthly savings scenarios.

For each scenario include:
1. Monthly savings amount
2. Six-month total
3. Assumptions behind the scenario

Use simple scenarios such as:
- Conservative
- Moderate
- Higher savings

Do not present the scenarios as guaranteed outcomes.
Do not execute financial transactions.
Do not invent income or expenses.
Do not provide personalized investment recommendations.
"""

    response = llm.invoke(prompt)

    return {
        "savings_scenarios": [response.content]
    }
