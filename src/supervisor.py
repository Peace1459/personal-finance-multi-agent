from langgraph.graph import StateGraph, START, END

from src.state import FinanceState

from src.agents.categorizer import categorizer_agent
from src.agents.budget import budget_agent
from src.agents.patterns import pattern_agent
from src.agents.savings import savings_agent
from src.agents.critic import critic_agent


def human_approval_node(state):
    """
    Handle human approval.

    Streamlit handles approval in the browser.
    The terminal version uses input().
    """

    # Streamlit/web interface:
    # stop here and let the browser display the approval buttons.
    if state.get("interface") == "web":
        return {
            "human_approved": None,
            "human_feedback": "",
        }

    # Terminal interface:
    print("\n==============================")
    print("HUMAN APPROVAL REQUIRED")
    print("==============================")

    print("\nThe Savings Advisor proposed:")
    print(state.get("savings_scenarios"))

    print("\nDo you approve these savings scenarios?")
    print("1 = Approve")
    print("2 = Reject")

    choice = input("\nEnter 1 or 2: ").strip()

    if choice == "1":
        print("\nHuman approval received.")

        return {
            "human_approved": True,
            "human_feedback": "User approved the savings scenarios.",
        }

    print("\nHuman rejection received.")

    feedback = input(
        "Briefly explain what should be changed: "
    ).strip()

    return {
        "human_approved": False,
        "human_feedback": feedback,
    }
    

def supervisor_router(state):
    """
    Decide which agent should act next.
    """

    # Stop if the critic approved the complete analysis.
    if state.get("approved") is True:
        return "end"

    revision_count = state.get("revision_count", 0)

    # Safety termination condition.
    if revision_count >= 3:
        return "end"

    # If the critic rejected the analysis, revise it.
    if state.get("approved") is False:
        return "budget"

    # If the human rejected the savings scenarios,
    # generate new savings scenarios.
    if state.get("human_approved") is False:
        return "savings"

    # Normal workflow.
    if not state.get("categorized_transactions"):
        return "categorizer"

    if not state.get("budget"):
        return "budget"

    if not state.get("spending_patterns"):
        return "patterns"

    if not state.get("savings_scenarios"):
        return "savings"

    # Require human approval before the critic.
    if state.get("human_approved") is None:

        if state.get("interface") == "web":
            return "end"

        return "human_approval"

    # Once human approval is received, send the analysis
    # to the critic.
    return "critic"


def supervisor_node(state):
    """
    Update supervisor-related state before routing.
    """

    # If the human rejected the savings scenarios,
    # clear the old scenarios and approval so that
    # the Savings Advisor creates new scenarios.
    if state.get("human_approved") is False:

        return {
            "revision_count": state.get("revision_count", 0) + 1,
            "savings_scenarios": [],
            "human_approved": None,
            "human_feedback": "",
            "approved": None,
            "critique": None,
        }

    # If the critic rejected the analysis,
    # clear downstream analysis and start a new revision.
    if state.get("approved") is False:

        return {
            "revision_count": state.get("revision_count", 0) + 1,
            "budget": {},
            "spending_patterns": [],
            "savings_scenarios": [],
            "human_approved": None,
            "human_feedback": "",
            "approved": None,
            "critique": None,
        }

    return {}


def build_graph():

    graph = StateGraph(FinanceState)

    # Supervisor
    graph.add_node("supervisor", supervisor_node)

    # Specialized agents
    graph.add_node("categorizer", categorizer_agent)
    graph.add_node("budget", budget_agent)
    graph.add_node("patterns", pattern_agent)
    graph.add_node("savings", savings_agent)

    # Human-in-the-loop
    graph.add_node("human_approval", human_approval_node)

    # Critic / risk checker
    graph.add_node("critic", critic_agent)

    # Start with supervisor.
    graph.add_edge(START, "supervisor")

    # Supervisor decides what happens next.
    graph.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "categorizer": "categorizer",
            "budget": "budget",
            "patterns": "patterns",
            "savings": "savings",
            "human_approval": "human_approval",
            "critic": "critic",
            "end": END,
        },
    )

    # After each worker, return to supervisor.
    graph.add_edge("categorizer", "supervisor")
    graph.add_edge("budget", "supervisor")
    graph.add_edge("patterns", "supervisor")
    graph.add_edge("savings", "supervisor")
    graph.add_edge("human_approval", "supervisor")
    graph.add_edge("critic", "supervisor")

    return graph.compile()
