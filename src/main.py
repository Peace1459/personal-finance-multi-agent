from dotenv import load_dotenv

from src.tools.visualization import create_spending_chart

from src.supervisor import build_graph
from src.tools.transaction_reader import read_transactions
from src.tools.calculator import (
    calculate_income,
    calculate_expenses,
    calculate_remaining,
)

load_dotenv()


# 1. Read transactions
transactions_df = read_transactions(
    "data/sample_transactions.csv"
)

transactions = transactions_df.to_dict("records")


# 2. Calculate basic financial figures
income = calculate_income(transactions)
expenses = calculate_expenses(transactions)
remaining = calculate_remaining(income, expenses)

# 2b. Create spending visualization
chart_path = create_spending_chart(
    transactions,
    "screenshots/spending_by_category.png"
)

print("\nSpending chart created:", chart_path)

# 3. Create the shared state
initial_state = {
    "user_query": (
        "Analyze my spending, create a budget, "
        "identify spending patterns, and create "
        "six-month savings scenarios."
    ),
    "transactions": transactions,
    "income": income,
    "expenses": expenses,
    "remaining": remaining,
    "revision_count": 0,
    "human_approved": None,
    "human_feedback": "",
}


# 4. Build the multi-agent workflow
graph = build_graph()


# 5. Run the workflow with streaming
print("\n==============================")
print("MULTI-AGENT WORKFLOW")
print("==============================")

final_result = initial_state.copy()

for update in graph.stream(initial_state):

    for node_name, state_update in update.items():

        print(f"\n[Agent/Node completed: {node_name}]")

        if node_name == "categorizer":
            print("Transaction categorization completed.")

        elif node_name == "budget":
            print("Budget analysis completed.")

        elif node_name == "patterns":
            print("Spending pattern analysis completed.")

        elif node_name == "savings":
            print("Savings scenarios generated.")

        elif node_name == "human_approval":
            print("Human approval stage completed.")

        elif node_name == "critic":
            print("Risk and compliance review completed.")

        elif node_name == "supervisor":
            print("Supervisor selected the next workflow step.")

        # Keep the latest complete state.
        if isinstance(state_update, dict):
            final_result.update(state_update)


# 6. Display the final shared state
print("\n==============================")
print("FINAL FINANCIAL ANALYSIS")
print("==============================")

print("\nIncome:", final_result["income"])
print("Expenses:", final_result["expenses"])
print("Remaining:", final_result["remaining"])

print("\n--- Categorized Transactions ---")
print(final_result.get("categorized_transactions"))

print("\n--- Budget Analysis ---")
print(final_result.get("budget"))

print("\n--- Spending Patterns ---")
print(final_result.get("spending_patterns"))

print("\n--- Savings Scenarios ---")
print(final_result.get("savings_scenarios"))

print("\n--- Human Review ---")
print("Human approved:", final_result.get("human_approved"))
print("Human feedback:", final_result.get("human_feedback"))

print("\n--- Critic ---")
print("Approved:", final_result.get("approved"))
print("Critique:", final_result.get("critique"))
