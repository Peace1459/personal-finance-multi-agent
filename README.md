# Personal Finance Assistant — Multi-Agent AI System

## 1. Project Overview

This project implements a multi-agent Personal Finance Assistant using Python, LangGraph, OpenAI, and Streamlit.

The system helps users analyze financial transactions, understand spending patterns, create a simple budget analysis, explore hypothetical savings scenarios, and receive a final risk and compliance review.

The system uses a supervisor to coordinate several specialized agents. A shared state is passed between the agents so that each agent can build on the results produced by previous agents.

The project provides both:

- A command-line workflow
- A Streamlit web application

---

## 2. Use Case and Rationale

The selected use case is a Personal Finance Assistant.

The goal is to help users:

- Analyze financial transactions
- Categorize spending
- Understand income and expenses
- Identify spending patterns
- Review possible savings scenarios
- Receive a final risk and compliance review

A multi-agent architecture is useful because each agent has a specific responsibility. This separates transaction classification, budget analysis, pattern detection, savings analysis, and review instead of asking one agent to perform every task.

---

## 3. System Architecture

The system contains five specialized agents:

1. Transaction Categorizer
2. Budget Analyst
3. Spending Pattern Detector
4. Savings Advisor
5. Risk and Compliance Critic

The Supervisor/Orchestrator controls the workflow.

### Architecture

```text
                     ┌──────────────────┐
                     │    Supervisor    │
                     │  / Orchestrator  │
                     └────────┬─────────┘
                              │
              ┌───────────────┼────────────────┐
              │               │                │
              ▼               ▼                ▼
        Categorizer        Budget          Patterns
              │               │                │
              └───────────────┼────────────────┘
                              │
                              ▼
                           Savings
                              │
                              ▼
                       Human Approval
                              │
                              ▼
                           Critic
                              │
                 ┌────────────┴────────────┐
                 │                         │
              APPROVED               NEEDS REVISION
                 │                         │
                 ▼                         ▼
                END                    Supervisor
```

## 4. Specialized Agents
**Transaction Categorizer**

The Transaction Categorizer classifies transactions into categories such as:

- Income
- Housing
- Food
- Transport
- Utilities
- Entertainment
- Shopping
- Healthcare
- Other

It does not calculate the budget or provide investment advice.

## Budget Analyst

The Budget Analyst uses the authoritative financial totals calculated by Python.

It reports:

-Total income
Total expenses
Remaining income
General budget observations
Areas where spending may be reviewed
Spending Pattern Detector

The Spending Pattern Detector examines categorized transactions and identifies:

Large spending categories
Frequent expenses
Recurring expenses
Potentially discretionary spending
Unusual observations

The Python-calculated financial totals are treated as authoritative.

Savings Advisor

The Savings Advisor creates three hypothetical savings scenarios:

Conservative
Moderate
Higher savings

Each scenario includes a monthly savings amount, six-month total, and assumptions.

The scenarios are presented as hypothetical rather than guaranteed outcomes.

Risk and Compliance Critic

The Critic reviews the outputs produced by the other agents.

It checks for:

Numerical inconsistencies
Unsupported claims
Invented transactions or amounts
Overly certain recommendations
Missing assumptions
Guaranteed financial outcomes

If problems are detected, the supervisor can send the workflow through a revision cycle.


## 5. Supervisor and Shared State

LangGraph is used to implement the workflow.

The supervisor decides which agent should act next.

The shared state contains information such as:

User query
Transactions
Categorized transactions
Income
Expenses
Remaining income
Budget analysis
Spending patterns
Savings scenarios
Critique
Approval status
Revision count
Human feedback
Interface type

The workflow terminates when the analysis is approved or when the maximum revision count is reached.

## 6. Tools

The project uses three main financial tools.

**Transaction Reader**

File:

[src/tools/transaction_reader.py](src/tools/transaction_reader.py)

Reads transaction data from the CSV file.

**Financial Calculator**

File:

[src/tools/calculator.py](src/tools/calculator.py)

Calculates:

Income
Expenses
Remaining income

Python performs these calculations so that important financial arithmetic is not dependent on language-model calculations.

**Visualization Tool**

File:

[src/tools/visualization.py](src/tools/visualization.py)

Creates a spending-by-category bar chart.

The generated chart is stored in:

screenshots/spending_by_category.png

## 7. Chat Intake

The web application also supports financial information provided directly through natural-language chat.

File:

[src/agents/chat_intake.py](src/agents/chat_intake.py)

The Chat Intake component extracts basic financial information such as income and common expense categories from the user's message.

For example, a user can provide information such as:

My monthly income is 150000. I spend 40000 on rent,
15000 on food, 10000 on transport, and 8000 on shopping.

The extracted amounts are converted into transaction records and passed into the same multi-agent workflow used by the CSV interface.

This allows the application to support both structured CSV data and conversational financial input.

## 8. Human-in-the-Loop

Before the final critic review, the system asks the human user to approve the proposed savings scenarios.

In the web application, the user can:

Approve the savings scenarios
Reject the scenarios and request a revision

If the user rejects the scenarios, they can provide written feedback.

The supervisor clears the previous savings scenarios and sends the workflow back to the Savings Advisor for revision.

This provides a human-in-the-loop safety mechanism.

## 9. Reflection and Revision Loop

The Critic provides a review of the completed analysis.

If the Critic identifies a problem, the supervisor starts a revision cycle.

A revision counter is maintained in the shared state.

The system has a maximum of three revisions as a safety termination condition.

The revision loop allows the system to reconsider generated financial analysis rather than immediately treating every agent output as final.

## 10. Streaming

The application uses LangGraph streaming to execute the workflow node by node.

Example workflow:

[supervisor]
[categorizer]
[supervisor]
[budget]
[supervisor]
[patterns]
[supervisor]
[savings]
[human_approval]
[critic]
[supervisor]

This provides visibility into workflow progress without exposing private model reasoning.

## 11. Streamlit Web Application

The project includes a Streamlit web interface in:

app.py

The web application provides two ways to provide financial information.

Option 1: CSV Upload

Users can upload a CSV file containing:

Date
Description
Amount

The application loads the transactions and sends them through the multi-agent workflow.

Option 2: Natural-Language Chat

Users can enter financial information directly into the chat interface.

The application extracts the financial amounts and sends them through the same workflow.

**Web Workflow**

```text
User Input
    │
    ▼
Chat Intake / CSV
    │
    ▼
Supervisor
    │
    ├── Categorizer
    ├── Budget Analyst
    ├── Pattern Detector
    └── Savings Advisor
             │
             ▼
      Human Approval
             │
             ▼
          Critic
             │
       ┌─────┴─────┐
       │           │
    Approved    Revision
       │           │
       ▼           ▼
      END      Supervisor
```

**Web Interface Screenshots**
- Main Interface

- Financial Analysis

- Human Approval

- Final Review

## 12. Example Financial Scenario

The sample dataset contains monthly transactions including:

Salary
Apartment rent
Supermarket purchases
Uber transactions
Netflix
Utilities
Restaurant spending
Clothing
Shopping

The Python financial calculations produce:

```
Income: 120000
Expenses: 88900
Remaining: 31100
```

The system then analyzes the transactions, identifies spending patterns, creates hypothetical savings scenarios, asks for human approval, and performs a final critic review.

## 13. Example Interaction

A typical workflow reaches the human approval stage:

HUMAN APPROVAL REQUIRED

The Savings Advisor proposed:

Conservative:
Monthly savings: 5,000
Six-month total: 30,000

Moderate:
Monthly savings: 10,000
Six-month total: 60,000

Higher:
Monthly savings: 15,000
Six-month total: 90,000

The user can approve the scenarios or request a revision.

After approval, the Risk and Compliance Critic reviews the completed analysis.

Example final result:

Human approval received.

Risk and compliance review completed.

Approved: True

Critique: APPROVED
## 14. Project Structure
```text
personal-finance-multi-agent/
│
├── data/
│   └── sample_transactions.csv
│
├── notebooks/
│   └── personal_finance_demo.ipynb
│
├── screenshots/
│   ├── spending_by_category.png
│   ├── notebook_spending_by_category.png
│   ├── web_interface.png
│   ├── web_financial_analysis.png
│   ├── web_human_approval.png
│   └── web_final_review.png
│
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── state.py
│   ├── supervisor.py
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── categorizer.py
│   │   ├── budget.py
│   │   ├── patterns.py
│   │   ├── savings.py
│   │   ├── critic.py
│   │   └── chat_intake.py
│   │
│   └── tools/
│       ├── __init__.py
│       ├── transaction_reader.py
│       ├── calculator.py
│       └── visualization.py
│
├── app.py
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```


## 15. Installation

Create and activate the virtual environment:
```
py -m venv .venv
.venv\Scripts\Activate.ps1
```
Install the dependencies:
```
python -m pip install -r requirements.txt
```

Create a .env file containing:
```
OPENAI_API_KEY=your_api_key_here
```
Do not commit the API key to GitHub.

## 16. Running the Command-Line Application

From the project root:
```
python -m src.main
```

The application reads the sample transaction data, calculates the financial totals, creates the spending chart, and runs the multi-agent workflow.

The application requests human approval before the final critic review.

## 17. Running the Web Application

From the project root, activate the virtual environment if necessary:
```
.venv\Scripts\Activate.ps1
```

Then run:
```
streamlit run app.py
```

Streamlit will provide a local web address where the application can be opened in a browser.

The web application supports:

- CSV transaction uploads
- Natural-language financial input
- Multi-agent financial analysis
- Spending pattern analysis
- Savings scenarios
- Human approval
- Revision requests
- Final risk and compliance review

## 18. Running the Notebook

Open:

[notebooks/personal_finance_demo.ipynb](notebooks/personal_finance_demo.ipynb)


Select the project's .venv Python kernel and run the cells in order.

The notebook demonstrates:

- Loading transaction data
- Calculating financial totals
- Creating a spending visualization
- Running the multi-agent workflow
- Human approval
- Final critic review

## 19. Challenges and Solutions
Challenge 1: Coordinating Multiple Agents

A simple sequential workflow would not demonstrate dynamic orchestration effectively.

Solution: LangGraph was used to create a supervisor that determines which agent should execute next.

Challenge 2: Numerical Consistency

Language models can produce inconsistent numerical calculations.

Solution: Python performs the authoritative income, expense, and remaining-income calculations. The other agents are instructed to use those values instead of recalculating them.

Challenge 3: Human Rejection

The system needed a mechanism to handle rejected savings scenarios.

Solution: Human feedback is stored in the shared state. When the user rejects the scenarios, the supervisor clears the previous scenarios and routes the workflow back to the Savings Advisor.

Challenge 4: Quality Control

Agent outputs may contain unsupported claims or inconsistencies.

Solution: A dedicated Risk and Compliance Critic reviews the completed analysis before termination.

Challenge 5: Preventing Infinite Revision

A revision loop could continue indefinitely.

Solution: The shared state maintains a revision count, and the supervisor terminates the workflow after a maximum of three revisions.

Challenge 6: Supporting Conversational Input

Users may not always have a CSV file available.

Solution: A Chat Intake component was added to extract basic income and expense information from natural-language messages and convert it into transaction records for the existing multi-agent workflow.

Challenge 7: Browser-Based Human Approval

The original command-line workflow used terminal input for human approval, which is not suitable for a browser interface.

Solution: The Streamlit application handles approval and revision requests through browser buttons and feedback fields while the LangGraph workflow continues to manage the agent coordination.

## 20. Technologies
- Python
- LangGraph
- LangChain
- OpenAI
- Streamlit
- Pandas
- Matplotlib
- Jupyter Notebook
- Python-dotenv


## 21. Reflection

Building this Personal Finance Assistant helped us clearly understand how multiple specialized AI agents work together as a single system. Instead of using one agent for every task, we divided the work among five agents: Transaction Categorizer, Budget Analyst, Spending Pattern Detector, Savings Advisor, and Risk and Compliance Critic. The LangGraph supervisor coordinates these agents and uses a shared state to pass information between them. We also learned the importance of using Python-based tools for calculations rather than relying on the LLM to perform important financial arithmetic.

One of the main challenges we encountered was making sure that the different agents do not produce inconsistent financial information. This was addressed by calculating the authoritative income, expenses, and remaining balance using Python before the agents run. The Critic agent then checks the analysis for numerical inconsistencies, unsupported claims, and overly certain recommendations. We also added human approval before the savings scenarios are accepted, which demonstrates how human oversight can be incorporated into an AI workflow.

The project showed us that a multi-agent system requires more than simply creating several AI agents. It requires agents with clearly defined responsibilities, an orchestrator, shared state, tools, validation, and termination conditions. Extending the project with a Streamlit web interface also demonstrated how an AI workflow can be turned into an interactive application. The project improved our understanding of LangGraph, Python project structure, Git, GitHub, Streamlit, and how to document and demonstrate an AI system using a notebook, screenshots, and a working web interface.