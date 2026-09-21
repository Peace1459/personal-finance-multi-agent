from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    timeout=30,
    max_retries=2
)


def budget_agent(state):
    income = state.get("income", 0)
    expenses = state.get("expenses", 0)
    remaining = income - expenses

    prompt = f"""
You are the Budget Analyst in a Personal Finance Assistant.

Analyze the following monthly financial information:

Income: {income}
Expenses: {expenses}
Remaining income: {remaining}

Create a simple budget analysis.

Include:
1. Total income
2. Total expenses
3. Remaining income
4. General observations about the budget
5. Areas where the user may want to review spending

Do not invent financial information.
Do not provide investment advice.
Clearly distinguish observations from assumptions.
"""

    response = llm.invoke(prompt)

    return {
        "remaining": remaining,
        "budget": {
            "analysis": response.content
        }
    }
