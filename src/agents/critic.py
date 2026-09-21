from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    timeout=30,
    max_retries=2
)


def critic_agent(state):
    income = state.get("income", 0)
    expenses = state.get("expenses", 0)
    remaining = state.get("remaining", 0)

    expected_remaining = income - expenses

    # Direct numerical validation using Python.
    if remaining != expected_remaining:
        return {
            "approved": False,
            "critique": (
                f"NEEDS_REVISION: Calculation error. "
                f"Expected remaining income to be {expected_remaining}, "
                f"but received {remaining}."
            )
        }

    prompt = f"""
You are the Risk and Compliance Critic in a Personal Finance Assistant.

Review the analysis produced by the other agents.

AUTHORITATIVE FINANCIAL VALUES
These values were calculated by Python and must be treated as correct:

Income: {income}
Expenses: {expenses}
Remaining: {remaining}

Budget analysis:
{state.get("budget")}

Spending patterns:
{state.get("spending_patterns")}

Savings scenarios:
{state.get("savings_scenarios")}

Check for:

1. Numerical inconsistencies with the authoritative values.
2. Unsupported claims.
3. Invented transactions or amounts.
4. Overly certain financial recommendations.
5. Missing assumptions.
6. Recommendations that could be interpreted as guaranteed outcomes.

Important:

- Do not reject the analysis merely because it does not contain
  information that was never provided.
- Do not invent additional financial obligations.
- Savings scenarios are hypothetical and may be accepted if they
  clearly state their assumptions.
- The authoritative income, expenses, and remaining values are:

  Income: {income}
  Expenses: {expenses}
  Remaining: {remaining}

Return exactly one of:

APPROVED

or

NEEDS_REVISION

Then provide a short explanation.
"""

    response = llm.invoke(prompt)
    critique = response.content

    approved = critique.strip().upper().startswith("APPROVED")

    return {
        "approved": approved,
        "critique": critique
    }
