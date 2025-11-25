# EPS Account Intelligence Agent (MVP)

An AI-powered agent that empowers Account Managers (AMs) to query distributed account intelligence (Salesforce, Google Drive, Gong, Slack, Gmail) via a unified chat interface. It strictly enforces "Source of Truth" rules defined in the PRD.

## 🚀 Features

*   **Source-Aware Retrieval**: Prioritizes Salesforce for dates/contracts and Drive/Highspot for strategy.
*   **Strict Citations**: Every fact is backed by a verifiable source link.
*   **Interactive Fallback**: If a document isn't found in the expected location (e.g., Drive), the agent asks permission before searching broadly.
*   **Polished CLI**: A beautiful, interactive command-line interface powered by `rich`.

## 🛠️ Architecture

*   **Brain**: OpenAI `gpt-4o` (via `EPS_ReAct_Agent.py`)
*   **Tools**: Custom Virtual Tools (`EPS_MCP_Tools.py`) wrapping the Glean AIA MCP Server.
*   **Protocol**: ReAct (Reasoning + Acting) loop.

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/tony-kipkemboi/EPS_Agent.git
    cd EPS_MCP
    ```

2.  **Set up environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configure Secrets**:
    Export your API keys (or add them to a `.env` file):
    ```bash
    export GLEAN_API_TOKEN="your-glean-token"
    export OPENAI_API_KEY="your-openai-key"
    ```

## 🏃‍♂️ Usage

Run the interactive agent from the project root:

```bash
python3 -m agents.EPS_ReAct_Agent_CLI
```

### Sample Queries
*   **Renewal Date**: "When is the renewal date for AdventHealth?"
*   **Risk Assessment**: "Are there any recent risks or concerns with JPMC?"
*   **Strategy**: "What are the key workforce goals for Hilton?"
*   **Emails**: "What was the last email from AdventHealth?"

## 📂 Project Structure

```
EPS_MCP/
├── agents/
│   ├── __init__.py
│   └── EPS_ReAct_Agent.py    # Main Agent Logic & CLI
├── tools/
│   ├── __init__.py
│   └── EPS_MCP_Tools.py      # Virtual Tool Definitions
├── EPS_Agent_Implementation_Strategy.md  # Architecture & V2 Roadmap
├── requirements.txt          # Dependencies
└── .gitignore
```

## 🔮 V2 Roadmap
*   **Quantitative Analysis**: Integration with OpenAI Code Interpreter for calculating spend trends and complex metrics.
*   **Multi-Account Queries**: "Compare participation rates across all Healthcare accounts."

