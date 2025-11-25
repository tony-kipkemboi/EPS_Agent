# EPS Account Intelligence Agent - Implementation Strategy

## 1. Executive Summary
**Goal:** Empower Account Managers (AMs) to query distributed account intelligence (Salesforce, GDrive, Gong, Gmail, Slack, Looker) via a unified chat interface.
**Core Technology:** Glean AIA MCP Server + Custom Orchestration Layer (Python Agent) + Databricks Hosting.
**Key Differentiator:** The agent must not just "search"; it must **enforce source prioritization** (e.g., "Renewal Date comes ONLY from Salesforce").

## 2. Data Source & Filter Mapping (Verified)

We will map the PRD's "Primary Data Sources" to specific MCP `search` tool queries using the `app:` filter.

| PRD Source | Priority | Content Type | MCP Query Strategy | PRD Specific Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Salesforce** | **Must-Have** | Account records, Dates, Contacts | `query + " app:salesforce"` | Renewal dates, EP contacts, Risk indicators |
| **Google Drive** | **Must-Have** | QBRs, Account Plans, Decks | `query + " app:googledrive"` | Strategic goals, Transition plans, Meeting notes |
| **Gong** | **Must-Have** | Call Transcripts, Sentiment | `query + " app:gong"` | "What did they say?", Objections, Sentiment |
| **Gmail** | **Must-Have** | Emails | `query + " app:gmail"` | Recent threads, Stakeholder comms |
| **Slack** | Nice-to-Have | Team Chatter | `query + " app:slack"` | Informal updates, "Who is working on this?" |
| **Looker** | **Must-Have** | Structured Metrics | `query + " app:looker"`* | Funnel tracking, Program performance, Enrollments |

*\*Note: For Looker, if Glean indexes the dashboards, we search for them. If specific metrics (e.g., "YTD Spend") are synced to Salesforce (as implied by "Budget tab in SFDC"), we prioritize Salesforce.*

## 3. Functional Implementation Strategy

### Level 1: Basic Retrieval (The "Source of Truth" Logic)
**Requirement:** "Retrieves renewal date from SFDC only." / "Who are main contacts?"
**Implementation:**
*   We will create a **Virtual Tool** `lookup_salesforce_data`.
*   **Logic:** When the LLM detects intent for "dates", "contacts", "status", or "contract value", it **MUST** call this tool.
*   **Code:** `mcp_client.call_tool("search", arguments={"query": f"{user_query} app:salesforce"})`
*   **Output:** Structured snippet from Salesforce.

### Level 2: Quantitative Interpretation (V2 Architecture)
**Requirement:** "Calculate spend trends," "Analyze portfolio patterns," "Compare participation rates."
**Challenge:** Standard LLMs are poor at arithmetic and aggregation over search snippets.
**Architecture Pivot:** **OpenAI Assistants API + Code Interpreter**.
*   **Why:** It provides a sandboxed Python environment to execute code.
*   **Workflow:**
    1.  Agent searches Salesforce/Looker for raw data (CSV/JSON format).
    2.  Agent passes data to **Code Interpreter**.
    3.  Agent writes Python logic (Pandas) to calculate exact sums, averages, or trends.
    4.  Agent returns precise numerical answers or generated charts (PNG).

### Level 3: Strategic Synthesis (The "Brain")
**Requirement:** "What workforce goals did [EP] identify in QBR? Synthesize with Gong calls."
**Implementation:**
*   **Step 1 (Drive):** Call `find_strategic_docs("workforce goals [Account]")` $\to$ Returns QBR Deck URL.
*   **Step 2 (Read):** Call `read_document(url)` $\to$ Extracts full text of the QBR.
*   **Step 3 (Gong):** Call `search_gong("workforce goals [Account]")` $\to$ Returns call snippets/transcripts.
*   **Step 4 (Synthesize):** The LLM combines the *planned* goals (Drive) with the *discussed* reality (Gong) to answer the user.

### Level 4: Interactive Fallback (New Usability Feature)
**Insight:** Strict filters (e.g., `app:googledrive`) can return zero results if a document is misfiled or permissions are restricted.
**Implementation:**
*   **Protocol:** If a specific tool returns "No results", the agent **MUST NOT** hallucinate or give up.
*   **Action:** The agent asks the user: "I couldn't find this in [Source]. Would you like me to search all sources?"
*   **Fallback:** If user approves, the agent calls `search_general_fallback` (unrestricted search).
*   **Verified:** Confirmed this successfully recovers documents from Highspot/Salesforce that were missing from Drive.

## 4. Technical Architecture (Python + Databricks)

### The Orchestrator (Agent Loop)
We will use a **ReAct (Reasoning + Acting)** loop.
1.  **User Input:** "What's the renewal date for AdventHealth and are they happy?"
2.  **Thought:** "I need two pieces of info: Renewal Date (Salesforce) and Sentiment (Gong/Drive)."
3.  **Action 1:** `lookup_salesforce_data("AdventHealth renewal date")`
4.  **Action 2:** `search_communications("AdventHealth sentiment risk")`
5.  **Observation:** [SFDC: 8/18/2027] + [Gong: "Concerns about reporting"]
6.  **Final Response:** "The renewal is 8/18/2027. Sentiment is generally positive, but they have concerns about reporting..."

### The "Virtual Tools" Wrapper (`EPS_MCP_Tools.py`)
We will abstract the raw MCP search into domain-specific functions to guide the LLM.

```python
async def search_salesforce(query: str):
    """Strictly for factual account data: dates, contracts, contacts."""
    return await mcp_search(f"{query} app:salesforce")

async def search_strategy_docs(query: str):
    """For QBRs, plans, and long-form documents."""
    return await mcp_search(f"{query} app:googledrive")

async def search_gong_and_slack(query: str):
    """For sentiment, voice of customer, and recent chatter."""
    # Can run parallel searches if needed
    return await mcp_search(f"{query} (app:gong OR app:slack)")

async def search_general_fallback(query: str):
    """Unrestricted search. Use ONLY with user permission after failure."""
    return await mcp_search(query)
```

## 5. Deployment Considerations (Databricks)
*   **Environment:** Databricks serves as the secure runtime.
*   **RBAC:** Databricks handles user auth; the Agent uses a Service Account or User Token for Glean.
*   **Interface:** Chat interface (Streamlit/App) connected to this backend.

## 6. MVP Validation Plan
We will test against the PRD's **"Sample Test Queries"**:
1.  *Level 0:* "What is the renewal date for Wellstar?" (Verified: Retrieves from SFDC)
2.  *Level 1:* "Who are key decision-makers?" (Verified: Retrieves from SFDC)
3.  *Level 3:* "What workforce goals did they identify in last QBR?" (Verified: Synthesizes from Drive/Highspot via Fallback)
