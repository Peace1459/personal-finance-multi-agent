import streamlit as st
import pandas as pd

from src.tools.calculator import (
    calculate_income,
    calculate_expenses,
    calculate_remaining,
)
from src.supervisor import build_graph
from src.agents.chat_intake import chat_intake_agent


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Personal Finance AI Assistant",
    page_icon="💰",
    layout="wide",
)

# ============================================================
# CUSTOM STYLING
# ============================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        font-size: 1.05rem;
        color: #666;
        margin-bottom: 1.5rem;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 650;
        margin-top: 1rem;
        margin-bottom: 0.6rem;
    }

    .status-box {
        padding: 1rem;
        border-radius: 0.6rem;
        border: 1px solid #ddd;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }

    .agent-box {
        padding: 0.8rem 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e5e5e5;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">💰 Personal Finance AI Assistant</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="subtitle">
    A multi-agent AI system for financial analysis, spending insights,
    savings planning, human approval, and final risk review.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "transactions" not in st.session_state:
    st.session_state.transactions = None

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "show_feedback" not in st.session_state:
    st.session_state.show_feedback = False

if "critic_revision_message" not in st.session_state:
    st.session_state.critic_revision_message = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("📁 Transaction Data")

    st.write(
        "Upload a CSV file or use the chat box "
        "to provide your financial information."
    )

    uploaded_file = st.file_uploader(
        "Upload transactions",
        type=["csv"],
    )

    if uploaded_file is not None:

        try:

            df = pd.read_csv(uploaded_file)

            required_columns = {
                "date",
                "description",
                "amount",
            }

            if not required_columns.issubset(
                df.columns
            ):

                st.error(
                    "CSV must contain: "
                    "date, description, amount"
                )

            else:

                st.session_state.transactions = (
                    df.to_dict("records")
                )

                st.success(
                    f"{len(df)} transactions loaded."
                )

                with st.expander(
                    "Preview transactions"
                ):

                    st.dataframe(
                        df,
                        use_container_width=True,
                    )

        except Exception as e:

            st.error(
                f"Could not read the CSV file: {e}"
            )

    st.divider()

    st.subheader("How it works")

    st.write(
        "1. Provide financial information"
    )

    st.write(
        "2. Specialized agents analyze it"
    )

    st.write(
        "3. Savings scenarios are generated"
    )

    st.write(
        "4. You approve or request a revision"
    )

    st.write(
        "5. A Critic performs the final review"
    )


# ============================================================
# HELPER FUNCTION
# ============================================================

def run_financial_analysis(
    transactions,
    user_query,
):

    income = calculate_income(
        transactions
    )

    expenses = calculate_expenses(
        transactions
    )

    remaining = calculate_remaining(
        income,
        expenses,
    )

    initial_state = {
        "user_query": user_query,
        "transactions": transactions,
        "income": income,
        "expenses": expenses,
        "remaining": remaining,
        "revision_count": 0,
        "human_approved": None,
        "human_feedback": "",
        "interface": "web",
    }

    graph = build_graph()

    final_result = initial_state.copy()

    for update in graph.stream(
        initial_state
    ):

        for (
            node_name,
            state_update,
        ) in update.items():

            if isinstance(
                state_update,
                dict,
            ):

                final_result.update(
                    state_update
                )

    return final_result


# ============================================================
# CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.write(
            message["content"]
        )


# ============================================================
# CHAT INPUT
# ============================================================

user_query = st.chat_input(
    "Ask about your finances..."
)


if user_query:

    st.session_state.analysis_result = None

    st.session_state.show_feedback = False

    st.session_state.critic_revision_message = None

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_query,
        }
    )

    # --------------------------------------------------------
    # CSV WORKFLOW
    # --------------------------------------------------------

    if (
        st.session_state.transactions
        is not None
    ):

        with st.spinner(
            "Running the finance agents..."
        ):

            result = run_financial_analysis(
                st.session_state.transactions,
                user_query,
            )

        st.session_state.analysis_result = (
            result
        )

    # --------------------------------------------------------
    # CHAT WORKFLOW
    # --------------------------------------------------------

    else:

        with st.spinner(
            "Understanding your financial information..."
        ):

            extracted_transactions = (
                chat_intake_agent(
                    user_query
                )
            )

        if not extracted_transactions:

            st.warning(
                "I couldn't extract financial "
                "amounts from that message. "
                "Please include your income "
                "and expenses."
            )

            st.stop()

        with st.spinner(
            "Running the finance agents..."
        ):

            result = run_financial_analysis(
                extracted_transactions,
                user_query,
            )

        st.session_state.analysis_result = (
            result
        )


# ============================================================
# ANALYSIS RESULTS
# ============================================================

result = st.session_state.analysis_result


if result:

    st.divider()

    st.markdown(
        '<div class="section-title">📊 Financial Analysis</div>',
        unsafe_allow_html=True,
    )


    # ========================================================
    # FINANCIAL SUMMARY
    # ========================================================

    st.subheader(
        "Financial Summary"
    )

    income = result.get(
        "income",
        0,
    )

    expenses = result.get(
        "expenses",
        0,
    )

    remaining = result.get(
        "remaining",
        0,
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Income",
            f"{income:,.2f}",
        )

    with col2:

        st.metric(
            "Expenses",
            f"{expenses:,.2f}",
        )

    with col3:

        st.metric(
            "Remaining",
            f"{remaining:,.2f}",
        )


    # ========================================================
    # BUDGET ANALYSIS
    # ========================================================

    st.subheader(
        "📋 Budget Analysis"
    )

    budget = result.get(
        "budget"
    )

    if budget:

        if isinstance(
            budget,
            dict,
        ):

            analysis = budget.get(
                "analysis",
                "",
            )

            if analysis:
                st.write(
                    analysis
                )

        else:

            st.write(
                budget
            )

    else:

        st.info(
            "Budget analysis is not available yet."
        )


    # ========================================================
    # SPENDING PATTERNS
    # ========================================================

    st.subheader(
        "🔎 Spending Patterns"
    )

    patterns = result.get(
        "spending_patterns"
    )

    if patterns:

        if isinstance(
            patterns,
            list,
        ):

            for pattern in patterns:

                st.markdown(
                    f'<div class="agent-box">{pattern}</div>',
                    unsafe_allow_html=True,
                )

        else:

            st.write(
                patterns
            )

    else:

        st.info(
            "No spending patterns were generated."
        )


    # ========================================================
    # SAVINGS SCENARIOS
    # ========================================================

    st.subheader(
        "💡 Savings Scenarios"
    )

    savings = result.get(
        "savings_scenarios"
    )

    if savings:

        if isinstance(
            savings,
            list,
        ):

            for scenario in savings:

                st.markdown(
                    f'<div class="agent-box">{scenario}</div>',
                    unsafe_allow_html=True,
                )

        else:

            st.write(
                savings
            )

    else:

        st.info(
            "No savings scenarios were generated."
        )


    # ========================================================
    # CRITIC REVISION MESSAGE
    # ========================================================

    if st.session_state.critic_revision_message:

        st.warning(
            "⚠️ The Risk and Compliance Critic "
            "requested a revision."
        )

        st.write(
            st.session_state.critic_revision_message
        )


    # ========================================================
    # HUMAN APPROVAL
    # ========================================================

    if (
        savings
        and result.get(
            "human_approved"
        ) is None
        and result.get(
            "approved"
        ) is not True
    ):

        st.divider()

        st.subheader(
            "👤 Human Approval Required"
        )

        st.write(
            "Review the proposed savings scenarios "
            "before the final risk and compliance review."
        )

        col1, col2 = st.columns(2)


        # ----------------------------------------------------
        # APPROVE
        # ----------------------------------------------------

        with col1:

            if st.button(
                "✅ Approve Savings Scenarios",
                type="primary",
                use_container_width=True,
            ):

                result[
                    "human_approved"
                ] = True

                result[
                    "human_feedback"
                ] = (
                    "User approved the savings scenarios."
                )

                with st.spinner(
                    "Running final risk and compliance review..."
                ):

                    graph = build_graph()

                    final_result = (
                        result.copy()
                    )

                    for update in graph.stream(
                        result
                    ):

                        for (
                            node_name,
                            state_update,
                        ) in update.items():

                            if isinstance(
                                state_update,
                                dict,
                            ):

                                final_result.update(
                                    state_update
                                )

                st.session_state.analysis_result = (
                    final_result
                )

                if (
                    final_result.get(
                        "approved"
                    )
                    is False
                ):

                    st.session_state.critic_revision_message = (
                        final_result.get(
                            "critique",
                            "The Critic requested a revision.",
                        )
                    )

                else:

                    st.session_state.critic_revision_message = None

                st.rerun()


        # ----------------------------------------------------
        # REJECT
        # ----------------------------------------------------

        with col2:

            if st.button(
                "🔄 Reject and Request Revision",
                use_container_width=True,
            ):

                st.session_state.show_feedback = True

                st.rerun()


    # ========================================================
    # REVISION REQUEST
    # ========================================================

    if st.session_state.show_feedback:

        st.divider()

        st.subheader(
            "🔄 Request a Revision"
        )

        feedback = st.text_input(
            "What would you like the Savings Advisor to change?"
        )

        if st.button(
            "Submit Revision Request",
            type="primary",
        ):

            if not feedback.strip():

                st.error(
                    "Please explain what should be changed."
                )

            else:

                result[
                    "human_approved"
                ] = False

                result[
                    "human_feedback"
                ] = feedback

                with st.spinner(
                    "Revising the savings scenarios..."
                ):

                    graph = build_graph()

                    revised_result = (
                        result.copy()
                    )

                    for update in graph.stream(
                        result
                    ):

                        for (
                            node_name,
                            state_update,
                        ) in update.items():

                            if isinstance(
                                state_update,
                                dict,
                            ):

                                revised_result.update(
                                    state_update
                                )

                st.session_state.analysis_result = (
                    revised_result
                )

                st.session_state.show_feedback = False

                st.session_state.critic_revision_message = None

                st.rerun()


    # ========================================================
    # RISK AND COMPLIANCE REVIEW
    # ========================================================

    critique = result.get(
        "critique"
    )

    approved = result.get(
        "approved"
    )

    if critique:

        st.divider()

        st.subheader(
            "🛡️ Risk and Compliance Review"
        )

        if approved is True:

            st.success(
                "✅ Final review approved."
            )

        elif approved is False:

            st.warning(
                "⚠️ The final review requested a revision."
            )

        st.write(
            critique
        )


    # ========================================================
    # HUMAN APPROVAL STATUS
    # ========================================================

    human_approved = result.get(
        "human_approved"
    )

    if human_approved is True:

        st.success(
            "👤 Human approval received."
        )

    elif human_approved is False:

        st.warning(
            "👤 The human reviewer requested a revision."
        )


    # ========================================================
    # FINAL STATUS
    # ========================================================

    if approved is True:

        st.divider()

        st.success(
            "🎉 Analysis completed successfully."
        )

        st.write(
            "The analysis passed both the human "
            "approval stage and the final critic review."
        )
        
