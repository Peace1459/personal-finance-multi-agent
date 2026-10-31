import os

import pandas as pd
import requests
import streamlit as st
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
# API CONFIGURATION
# ============================================================

API_BASE_URL = os.getenv(
    "FINANCE_API_URL",
    "http://127.0.0.1:8000",
)

API_TIMEOUT_SECONDS = 15
# ============================================================
# CROSS-IMPORT DUPLICATE REVIEW API HELPERS
# ============================================================

def fetch_cross_import_duplicates(status="pending"):
    """Fetch cross-import duplicate candidates from the API."""

    response = requests.get(
        f"{API_BASE_URL}/cross-import-duplicates",
        params={"status": status} if status != "all" else {},
        timeout=API_TIMEOUT_SECONDS,
    )

    response.raise_for_status()
    return response.json()


def update_cross_import_duplicate(duplicate_id, status):
    """Confirm or dismiss a duplicate candidate."""

    if status not in {"confirmed", "dismissed"}:
        raise ValueError(
            "Status must be 'confirmed' or 'dismissed'."
        )

    response = requests.patch(
        f"{API_BASE_URL}/cross-import-duplicates/{duplicate_id}",
        json={"status": status},
        timeout=API_TIMEOUT_SECONDS,
    )

    response.raise_for_status()
    return response.json()

def fetch_import_history():
    """Fetch saved CSV import history from the API."""

    response = requests.get(
        f"{API_BASE_URL}/imports",
        timeout=API_TIMEOUT_SECONDS,
    )

    response.raise_for_status()
    return response.json()


def fetch_transaction_categories():
    """Fetch available transaction categories from the API."""

    response = requests.get(
        f"{API_BASE_URL}/transaction-categories",
        timeout=API_TIMEOUT_SECONDS,
    )

    response.raise_for_status()
    return response.json().get("categories", [])



def fetch_import_transactions(
    import_id=None,
    search=None,
    category=None,
    transaction_type=None,
    start_date=None,
    end_date=None,
):
    """Fetch transactions using optional filters."""

    params = {
        "import_id": import_id,
        "search": search,
        "category": category,
        "transaction_type": transaction_type,
        "start_date": start_date,
        "end_date": end_date,
    }

    # Remove parameters that were not provided.
    params = {
        key: value
        for key, value in params.items()
        if value is not None and value != ""
    }

    response = requests.get(
        f"{API_BASE_URL}/transactions",
        params=params,
        timeout=API_TIMEOUT_SECONDS,
    )

    response.raise_for_status()
    return response.json()

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
        if st.button("Import CSV", use_container_width=True):

            try:
                file_bytes = uploaded_file.getvalue()

                # Validate the CSV locally for the existing agent workflow.
                df = pd.read_csv(uploaded_file)

                required_columns = {
                    "date",
                    "description",
                    "amount",
                }

                if not required_columns.issubset(df.columns):
                    st.error(
                        "CSV must contain: date, description, amount"
                    )

                else:
                    # Send the original CSV to the persistent import API.
                    response = requests.post(
                        f"{API_BASE_URL}/transactions/import",
                        files={
                            "file": (
                                uploaded_file.name,
                                file_bytes,
                                "text/csv",
                            )
                        },
                        timeout=API_TIMEOUT_SECONDS,
                    )

                    response.raise_for_status()
                    import_data = response.json()

                    # Preserve the existing finance-agent workflow.
                    st.session_state.transactions = df.to_dict(
                        orient="records"
                    )

                    st.session_state.import_id = import_data["import_id"]

                    st.success("CSV imported and saved successfully.")

                    st.write(
                        f"**Import ID:** {import_data['import_id']}"
                    )
                    st.write(
                        f"**Transactions imported:** "
                        f"{import_data['imported_rows']}"
                    )
                    st.write(
                        f"**Import issues:** "
                        f"{import_data['issue_count']}"
                    )
                    st.write(
                        f"**Within-file duplicate groups:** "
                        f"{import_data['duplicate_group_count']}"
                    )

                    with st.expander("Preview transactions"):
                        st.dataframe(
                            df,
                            use_container_width=True,
                        )

            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 409:
                    try:
                        detail = exc.response.json().get(
                            "detail",
                            "This CSV has already been imported.",
                        )
                    except ValueError:
                        detail = "This CSV has already been imported."

                    st.warning(detail)
                else:
                    st.error(f"Import failed: {exc}")

            except requests.RequestException as exc:
                st.error(f"Could not connect to the FinanceAI API: {exc}")

            except Exception as exc:
                st.error(f"Could not process the CSV file: {exc}")


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
# TRANSACTION MANAGEMENT
# ============================================================

st.divider()
st.header("Transaction Management")

st.write(
    "Search and filter transactions saved across all imports."
)

with st.form("transaction_filter_form"):

    search_term = st.text_input(
        "Search description or merchant",
        placeholder="e.g. Naivas, Uber, Rent",
    )

    col1, col2 = st.columns(2)

    with col1:
        try:
            available_categories = fetch_transaction_categories()

            category_options = ["All"] + available_categories

            category_filter = st.selectbox(
                 "Category",
                options=category_options,
    )

        except requests.RequestException as exc:
            st.error(f"Could not load transaction categories: {exc}")
            category_filter = "All"
        start_date_filter = st.date_input(
            "Start date",
            value=None,
        )

    with col2:
        transaction_type_filter = st.selectbox(
            "Transaction type",
            options=["All", "Income", "Expense"],
        )

        end_date_filter = st.date_input(
            "End date",
            value=None,
        )

    submitted = st.form_submit_button(
        "Search Transactions",
        use_container_width=True,
    )

if submitted:

    if (
        start_date_filter is not None
        and end_date_filter is not None
        and start_date_filter > end_date_filter
    ):
        st.error("Start date cannot be after end date.")

    else:
        try:
            result = fetch_import_transactions(
                search=search_term,
                category=(
                    None
                    if category_filter == "All"
                    else category_filter
                ),
                transaction_type=(
                    None
                    if transaction_type_filter == "All"
                    else transaction_type_filter
                ),
                start_date=(
                    start_date_filter.isoformat()
                    if start_date_filter is not None
                    else None
                ),
                end_date=(
                    end_date_filter.isoformat()
                    if end_date_filter is not None
                    else None
                ),
            )

            transactions = result.get("transactions", [])

            st.write(
                f"Matching transactions: {result.get('count', 0)}"
            )

            if transactions:
                transactions_df = pd.DataFrame(transactions)

                st.dataframe(
                    transactions_df,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No transactions match your filters.")

        except requests.RequestException as exc:
            st.error(f"Could not retrieve transactions: {exc}")


# ============================================================
# IMPORT HISTORY
# ============================================================

st.divider()
st.header("Import History")

if st.button("Refresh import history"):
    st.rerun()

try:
    history_data = fetch_import_history()
    imports = history_data.get("imports", [])

    if imports:
        history_df = pd.DataFrame(imports)

        history_df = history_df.rename(
            columns={
                "id": "Import ID",
                "created_at": "Import Date",
                "total_rows": "Total Rows",
                "imported_rows": "Imported Rows",
                "issue_count": "Issues",
                "duplicate_group_count": "Duplicate Groups",
                "duplicate_row_count": "Duplicate Rows",
                "category_review_count": "Category Reviews",
                "total_rows_requiring_review": "Rows Requiring Review",
            }
        )

        st.caption(f"Total imports: {len(imports)}")

        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # IMPORT DETAILS
        # ----------------------------------------------------

        st.subheader("View Import Details")

        import_options = {
            (
                f"{batch['created_at'][:10]} | "
                f"{batch['imported_rows']} transactions | "
                f"{batch['id'][:8]}"
            ): batch["id"]
            for batch in imports
        }

        selected_import_label = st.selectbox(
            "Select an import",
            options=list(import_options.keys()),
            key="selected_import_history",
        )

        selected_import_id = import_options[
            selected_import_label
        ]

        if st.button(
            "View Transactions",
            use_container_width=True,
        ):
            try:
                detail_data = fetch_import_transactions(
                    selected_import_id
                )

                transactions = detail_data.get(
                    "transactions", []
                )

                if transactions:
                    st.write(
                        f"Transactions found: "
                        f"{detail_data['count']}"
                    )

                    transactions_df = pd.DataFrame(
                        transactions
                    )

                    st.dataframe(
                        transactions_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                else:
                    st.info(
                        "No transactions found for this import."
                    )

            except requests.RequestException as exc:
                st.error(
                    f"Could not retrieve import details: {exc}"
                )

    else:
        st.info("No CSV imports have been saved yet.")

except requests.RequestException as exc:
    st.error(f"Could not load import history: {exc}")

# ============================================================
# CROSS-IMPORT DUPLICATE REVIEW
# ============================================================

st.divider()
st.header("Cross-Import Duplicate Review")

st.write(
    "Review transactions that may have been imported more than once. "
    "Confirm or dismiss each candidate without deleting either transaction."
)

review_filter = st.selectbox(
    "Filter candidates by status",
    options=["pending", "confirmed", "dismissed", "all"],
    format_func=lambda value: value.capitalize(),
    key="cross_import_review_filter",
)

if st.button("Refresh duplicate candidates"):
    st.rerun()

try:
    duplicate_data = fetch_cross_import_duplicates(
        status=review_filter
    )
    duplicates = duplicate_data.get("duplicates", [])

    st.caption(
        f"{duplicate_data.get('count', len(duplicates))} candidate(s) found"
    )

    if not duplicates:
        st.info("No duplicate candidates found for this status.")

    for duplicate in duplicates:
        duplicate_id = duplicate["id"]
        current_status = duplicate.get("status", "pending")

        with st.container(border=True):
            st.subheader(f"Candidate #{duplicate_id}")

            st.write(
                f"**Status:** {current_status.capitalize()}"
            )
            st.write(f"**Reason:** {duplicate.get('reason', 'Not provided')}")

            new_tx = duplicate["new_transaction"]
            existing_tx = duplicate["existing_transaction"]

            new_col, existing_col = st.columns(2)

            with new_col:
                st.markdown("**New transaction**")
                st.write(f"**Date:** {new_tx.get('transaction_date', '—')}")
                st.write(f"**Description:** {new_tx.get('description', '—')}")
                st.write(f"**Amount:** {new_tx.get('amount', '—')}")
                st.write(f"**Merchant:** {new_tx.get('merchant') or '—'}")
                st.write(f"**Category:** {new_tx.get('category', '—')}")
                st.write(f"**Import ID:** {new_tx.get('import_id', '—')}")

            with existing_col:
                st.markdown("**Existing transaction**")
                st.write(
                    f"**Date:** {existing_tx.get('transaction_date', '—')}"
                )
                st.write(
                    f"**Description:** {existing_tx.get('description', '—')}"
                )
                st.write(f"**Amount:** {existing_tx.get('amount', '—')}")
                st.write(
                    f"**Merchant:** {existing_tx.get('merchant') or '—'}"
                )
                st.write(f"**Category:** {existing_tx.get('category', '—')}")
                st.write(
                    f"**Import ID:** {existing_tx.get('import_id', '—')}"
                )

            if current_status == "pending":
                confirm_col, dismiss_col = st.columns(2)

                with confirm_col:
                    if st.button(
                        "Confirm duplicate",
                        key=f"confirm_duplicate_{duplicate_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        try:
                            update_cross_import_duplicate(
                                duplicate_id,
                                "confirmed",
                            )
                            st.success(
                                f"Candidate #{duplicate_id} confirmed."
                            )
                            st.rerun()
                        except requests.RequestException as exc:
                            st.error(
                                f"Could not confirm candidate: {exc}"
                            )

                with dismiss_col:
                    if st.button(
                        "Dismiss candidate",
                        key=f"dismiss_duplicate_{duplicate_id}",
                        use_container_width=True,
                    ):
                        try:
                            update_cross_import_duplicate(
                                duplicate_id,
                                "dismissed",
                            )
                            st.success(
                                f"Candidate #{duplicate_id} dismissed."
                            )
                            st.rerun()
                        except requests.RequestException as exc:
                            st.error(
                                f"Could not dismiss candidate: {exc}"
                            )

except requests.RequestException as exc:
    st.error(
        "Could not connect to the FinanceAI API. "
        "Check that the FastAPI server is running at "
        f"{API_BASE_URL}. Details: {exc}"
    )



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

