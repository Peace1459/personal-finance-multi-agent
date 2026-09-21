# Personal Finance Assistant — Multi-Agent AI System

## 1. Project Overview

This project implements a multi-agent Personal Finance Assistant using Python, LangGraph, and OpenAI.

The system helps a user analyze financial transactions, understand spending patterns, create a simple budget analysis, and explore hypothetical savings scenarios.

The system uses a supervisor to coordinate several specialized agents. A shared state is passed between the agents so that each agent can build on the results produced by previous agents.

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
                    │     Supervisor   │
                    │   / Orchestrator │
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
                 ┌───────────┴───────────┐
                 │                       │
              APPROVED              NEEDS REVISION
                 │                       │
                 ▼                       ▼
                END                 Supervisor
```

## 4. Specialized Agents
### Transaction Categorizer

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

### Budget Analyst

The Budget Analyst uses the authoritative financial totals calculated by Python.

It reports:

- Total income
- Total expenses
- Remaining income
- General budget observations
- Areas where spending may be reviewed
- Spending Pattern Detector

The Spending Pattern Detector examines categorized transactions and identifies:

- Large spending categories
- Frequent expenses
- Recurring expenses
- Potentially discretionary spending
- Unusual observations

The Python-calculated financial totals are treated as authoritative.

### Savings Advisor

The Savings Advisor creates three hypothetical savings scenarios:

- Conservative
- Moderate
- Higher savings

Each scenario includes a monthly savings amount, six-month total, and assumptions.

The scenarios are presented as hypothetical rather than guaranteed outcomes.

### Risk and Compliance Critic

The Critic reviews the outputs produced by the other agents.

It checks for:

- Numerical inconsistencies
- Unsupported claims
- Invented transactions or amounts
- Overly certain recommendations
- Missing assumptions
- Guaranteed financial outcomes

If problems are detected, the supervisor can send the workflow through a revision cycle.


## 5. Supervisor and Shared State

LangGraph is used to implement the workflow.

The supervisor decides which agent should act next.

The shared state contains information such as:

- User query
- Transactions
- Categorized transactions
- Income
- Expenses
- Remaining income
- Budget analysis
- Spending patterns
- Savings scenarios
- Critique
- Approval status
- Revision count
- Human feedback

The workflow terminates when the analysis is approved or when the maximum revision count is reached.


## 6. Tools

The project uses three tools.

**Transaction Reader**

File:

[src/tools/transaction_reader.py](src/tools/transaction_reader.py)

Reads transaction data from the CSV file.

**Financial Calculator**

File:

[src/tools/calculator.py](src/tools/calculator.py)

Calculates:

- Income
- Expenses
- Remaining income

**Visualization Tool**

File:

[src/tools/visualization.py](src/tools/visualization.py)

Creates a spending-by-category bar chart.

The generated chart is stored in:

[screenshots/spending_by_category.png](screenshots/spending_by_category.png)


## 7. Human-in-the-Loop

Before the final critic review, the system asks the human user to approve the proposed savings scenarios.

The user can:
1 = Approve
2 = Reject

If the user rejects the scenarios, they can provide feedback. The supervisor clears the previous savings scenarios and sends the workflow back to the Savings Advisor for revision.

This provides a human-in-the-loop safety mechanism.

## 8. Reflection and Revision Loop

The Critic provides a review of the completed analysis.

If the Critic identifies a problem, the supervisor starts a revision cycle.

A revision counter is maintained in the shared state.

The system has a maximum of three revisions as a safety termination condition.

## 9. Streaming

The application uses LangGraph streaming to display workflow progress.

Example:
```
[Agent/Node completed: supervisor]
[Agent/Node completed: categorizer]
[Agent/Node completed: supervisor]
[Agent/Node completed: budget]
[Agent/Node completed: supervisor]
[Agent/Node completed: patterns]
[Agent/Node completed: supervisor]
[Agent/Node completed: savings]
[Agent/Node completed: human_approval]
[Agent/Node completed: critic]
```
This provides visibility into which workflow node has completed without exposing private model reasoning.

## 10. Example of Financial Scenario

The sample dataset contains monthly transactions including:

- Salary
- Apartment rent
- Supermarket purchases
- Uber transactions
- Netflix
- Utilities
- Restaurant spending
- Clothing
- Shopping

The Python financial calculations produce:
```
Income: 120000
Expenses: 88900
Remaining: 31100
```
The system then analyzes the transactions, identifies spending patterns, creates hypothetical savings scenarios, asks for human approval, and performs a final critic review.

## 11. Example Interaction
```text
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

1 = Approve
2 = Reject
Enter 1 or 2: 1

Human approval received.

Risk and compliance review completed.

Approved: True
Critique: APPROVED
```

## 12. Project Structure
``` text 
personal-finance-multi-agent/
│
├── data/
│   └── sample_transactions.csv
│
├── notebooks/
│   └── personal_finance_demo.ipynb
│
├── screenshots/
│   └── spending_by_category.png
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
│   │   └── critic.py
│   │
│   └── tools/
│       ├── __init__.py
│       ├── transaction_reader.py
│       ├── calculator.py
│       └── visualization.py
│
├── .env
├── .gitignore
├── README.md
└── requirements.txt
``` 

## 13. Installation

Create and activate the virtual environment:
``` </>PowerShell
py -m venv .venv
.venv\Scripts\Activate.ps1
```
Install the dependencies:
```</>PowerShell
python -m pip install -r requirements.txt
```

Create a .env file containing:
```
OPENAI_API_KEY=your_api_key_here
```
Do not commit the API key to GitHub.


## 14. Running the Application

From the project root:
```
python -m src.main
```

The application reads the sample transaction data, calculates the financial totals, creates the spending chart, and runs the multi-agent workflow.

The application will request human approval before the final critic review.

## 15. Running the Notebook

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

## **16. Challenges and Solutions**
**Challenge 1:** Coordinating Multiple Agents

A simple sequential workflow would not demonstrate dynamic orchestration effectively.

**Solution:** LangGraph was used to create a supervisor that determines which agent should execute next.

**Challenge 2:** Numerical Consistency

Language models can produce inconsistent numerical calculations.

**Solution:** Python performs the authoritative income, expense, and remaining-income calculations. The other agents are instructed to use those values instead of recalculating them.

**Challenge 3:** Human Rejection

The system needed a mechanism to handle rejected savings scenarios.

**Solution:** Human feedback is stored in the shared state. When the user rejects the scenarios, the supervisor clears the previous scenarios and routes the workflow back to the Savings Advisor.

**Challenge 4:** Quality Control

Agent outputs may contain unsupported claims or inconsistencies.

**Solution:** A dedicated Risk and Compliance Critic reviews the completed analysis before termination.

**Challenge 5:** Preventing Infinite Revision

A revision loop could continue indefinitely.

**Solution:** The shared state maintains a revision count, and the supervisor terminates the workflow after a maximum of three revisions.

## 17. Technologies
- Python
- LangGraph
- LangChain
- OpenAI
- Pandas
- Matplotlib
- Jupyter Notebook
- Python-dotenv



## 19. **Reflection**
Building this Personal Finance Assistant helped us clearly understand how multiple specialized AI agents work together as a single system. Instead of using one agent for every task, we devided the work among five agents, i.e, Transaction Categorizer, Budget Analyst, Spending Pattern Detector, Savings Analyzer, and Risk and Compliance Critic. The langGraph supervisor coordinates these agents and uses a shared state to pass information between them. We also learned the importance of using Python-based tools for calculations rather than relying on the LLM to perform important financial arithmetic.

One of the main challenges we encountered was making sure that the different agents do not produce inconsistent financial information. This was addressed by calculating the authoritative income, expenses, and the remaining balance using Python before the agents run. The critic agent then checks the analysis for numerical inconsistencies, unsupported claims, and overly certain recommendations. We also added human approval beefore the savings scenarios are accepted, which demonstrates how human oversight can be incorporated into an AI workflow.

The project showed us that a multi-agent system requires more than simply creating several AI agents, but instead agents with clearly defined responsibilities, an orchestrator, shared state, tools, validation, and termination conditions. The project also improved our understanding of LangGraph, Python project structure, Git, GitHub, and how to document and demonstrate an AI system using a notebook and screenshots.

