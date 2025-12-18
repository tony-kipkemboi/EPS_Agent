"""
EPS Account Intelligence Agent - CLI Version (OpenAI Responses Pattern)

A standalone CLI for testing the Responses API agent locally.
Uses OpenAI directly (no Databricks required).

Usage:
    python eps_agent_cli.py

Prerequisites:
    - GLEAN_API_TOKEN: Your Glean API token
    - GLEAN_INSTANCE: Your Glean instance (e.g., guild-be.glean.com)
    - OPENAI_API_KEY: Your OpenAI API key
"""

import json
import os
import sys
from typing import Any, Callable, Generator, Optional
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live

# Load environment variables
load_dotenv()

console = Console()


# =============================================================================
# CONFIGURATION
# =============================================================================

LLM_MODEL = "gpt-5.1"  # or "gpt-4o" for better quality

# Global Glean credentials (loaded from environment at import time)
_glean_api_token: Optional[str] = os.environ.get("GLEAN_API_TOKEN")
_glean_instance: Optional[str] = os.environ.get("GLEAN_INSTANCE")


# =============================================================================
# SYSTEM PROMPT (PRD-aligned)
# =============================================================================

SYSTEM_PROMPT = """
# EPS Account Intelligence Agent

You help Account Managers retrieve and synthesize account intelligence across Salesforce, Google Drive, Gong, Gmail, and Slack. 
You synthesize findings into coherent, citation-backed summaries.

## EXECUTION MODEL

Follow these steps for EVERY query:

### Step 1: ANALYZE
Parse the user's complete question to identify:
- Account name (and common variations like "JPMC" = "JPMorgan Chase")
- All information requested (often multi-part questions)
- Relevant time constraints

### Step 2: PLAN & EXECUTE
Call ALL necessary tools in parallel. Do NOT pause for permission between tools.

<example>
User: "Who are the decision makers at AdventHealth and what are their priorities?"

Analysis: Needs (1) contacts/decision makers AND (2) priorities
Tools needed: search_salesforce_contacts + search_communications + search_strategy_docs
Action: Call all 3 tools in parallel, then synthesize
</example>

<example>
User: "When is Target's renewal and are there any risks?"

Analysis: Needs (1) renewal date AND (2) risk indicators
Tools needed: search_salesforce_opportunities + search_communications
Action: Call both tools in parallel, then synthesize
</example>

### Step 3: SYNTHESIZE
After ALL tools return, provide a unified response with:
- Clear answer to each part of the question
- Source citations for every fact
- Explicit gaps if data is missing

## DATA SOURCE ROUTING

| Question Type | Tool | Notes |
|---------------|------|-------|
| Renewal dates, contracts, deals | search_salesforce_opportunities | Definitive source for dates |
| Account overview, company info | search_salesforce_accounts | Account-level data |
| Contacts, stakeholders, roles | search_salesforce_contacts | Key decision makers |
| Metrics, dashboards, spend | search_metrics_and_dashboards | Looker data |
| QBRs, account plans, strategy | search_strategy_docs | Google Drive |
| Calls, emails, sentiment | search_communications | Gong, Slack, Gmail |

## QUERY CONSTRUCTION

Place the account name FIRST in your query for better ranking:
- ✓ "AdventHealth renewal date"
- ✓ "Target key contacts"
- ✗ "renewal date AdventHealth"

For communications, you may use OR variations:
- "("AdventHealth" OR "Advent Health") recent concerns"

## CITATION FORMAT (REQUIRED)

Every factual claim MUST include a citation:
`[Source: Document Title (Source, Date) - URL]`

Example: The renewal is August 2026. [Source: AdventHealth - Grow - 2026-08 - Renewal (Salesforce) - https://salesforce.com/...]

## HANDLING MISSING DATA

1. State what you could NOT find: "I could not locate X in [Source]."
2. Suggest next step: "Would you like me to search all sources?"
3. Only call search_general_fallback if user approves.

Never hallucinate or invent information.
"""


# =============================================================================
# GLEAN API
# =============================================================================

def _get_glean_api_url() -> str:
    """Get the Glean API URL."""
    if not _glean_instance:
        raise RuntimeError("GLEAN_INSTANCE not set")
    
    clean = _glean_instance.replace("https://", "").replace("http://", "").rstrip("/")
    
    # Handle short form: "guild" → "guild-be.glean.com"
    if "." not in clean:
        clean = f"{clean}-be.glean.com"
    
    return f"https://{clean}/rest/api/v1/search"


def discover_datasource_facets(datasource: str) -> dict:
    """
    Discover available facets for a specific datasource.
    
    Per Glean docs: https://developers.glean.com/guides/search/datasource-filters
    This returns the facetResults which show all available facets for filtering.
    
    Args:
        datasource: The datasource name (e.g., "salescloud", "gong", "gdrive")
    
    Returns:
        Dict with facet names and their available values
    """
    if not _glean_api_token:
        raise RuntimeError("Glean API token not set")
    
    headers = {"Authorization": f"Bearer {_glean_api_token}"}
    
    # Use pageSize=0 and responseHints=["FACET_RESULTS"] for efficiency
    payload = {
        "query": "test",
        "pageSize": 0,
        "requestOptions": {
            "facetBucketSize": 100,
            "facetFilters": [
                {
                    "fieldName": "app",
                    "values": [{"value": datasource, "relationType": "EQUALS"}]
                }
            ],
            "responseHints": ["FACET_RESULTS"]
        }
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(_get_glean_api_url(), headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            facet_results = data.get("facetResults", [])
            
            # Extract facet names and sample values
            facets = {}
            for facet in facet_results:
                source_name = facet.get("sourceName", "unknown")
                buckets = facet.get("buckets", [])
                values = [b.get("value", {}).get("stringValue", "") for b in buckets[:10]]
                facets[source_name] = values
            
            return facets
            
    except Exception as e:
        return {"error": str(e)}


def glean_search(
    query: str, 
    datasources: Optional[list[str]] = None, 
    num_results: int = 10,
    facet_filters: Optional[list[dict]] = None
) -> list[dict]:
    """
    Search Glean via REST API with proper filtering.
    
    Uses Glean's official requestOptions for filtering:
    - datasourcesFilter: limit to specific apps (salescloud, gong, etc.)
    - facetFilters: filter by type, from, last_updated_at, etc.
    
    Args:
        query: Search query
        datasources: List of datasource names (e.g., ["salescloud"], ["gong", "slack"])
        num_results: Number of results to return
        facet_filters: List of facet filter objects per Glean API spec
                       Example: [{"fieldName": "type", "values": [{"value": "opportunity", "relationType": "EQUALS"}]}]
    """
    if not _glean_api_token:
        raise RuntimeError("Glean API token not set")
    
    headers = {"Authorization": f"Bearer {_glean_api_token}"}
    
    console.print(f"  [dim]   → Query: \"{query}\"[/dim]")
    
    # Build requestOptions with proper filtering (per Glean API docs)
    request_options = {
        "facetBucketSize": 100,
        "returnLlmContentOverSnippets": True,
    }
    
    # Add datasource filter
    if datasources:
        request_options["datasourcesFilter"] = datasources
        console.print(f"  [dim]   → Datasources: {datasources}[/dim]")
    
    # Add facet filters (e.g., type:opportunity)
    if facet_filters:
        request_options["facetFilters"] = facet_filters
        filter_desc = ", ".join([f"{f['fieldName']}={f['values'][0]['value']}" for f in facet_filters if f.get('values')])
        console.print(f"  [dim]   → Type filter: {filter_desc}[/dim]")
    
    payload = {
        "query": query,
        "pageSize": num_results,
        "maxSnippetSize": 4000,
        "requestOptions": request_options
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(_get_glean_api_url(), headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            # Debug: show result count
            console.print(f"  [dim]   → Glean returned {len(results)} results[/dim]")
            
            formatted = []
            for r in results:
                doc = r.get("document", {})
                
                # Prefer llmContent over snippets for richer content
                # llmContent is provided when returnLlmContentOverSnippets=True
                content = r.get("llmContent") or r.get("snippets", [])
                
                formatted.append({
                    "title": doc.get("title", "Untitled"),
                    "url": doc.get("url", ""),
                    "snippets": content,  # Use llmContent if available
                    "datasource": doc.get("datasource", ""),
                    "author": doc.get("author", {}).get("name", "Unknown"),
                    "updatedAt": doc.get("updateTime", "")
                })
            return formatted
            
    except httpx.HTTPStatusError as e:
        console.print(f"  [red]   → API Error: {e.response.status_code} - {e.response.text[:200]}[/red]")
        return [{"error": f"Glean API error: {e.response.status_code}"}]
    except Exception as e:
        console.print(f"  [red]   → Error: {e}[/red]")
        return [{"error": f"Glean error: {e}"}]


def format_results(results: list[dict], source_name: str) -> str:
    """Format search results for LLM with datasource verification."""
    if not results:
        return f"No results found in {source_name}."
    
    if results[0].get("error"):
        return results[0]["error"]
    
    # Collect unique datasources for verification
    datasources_found = set()
    
    formatted = []
    for i, r in enumerate(results[:5], 1):
        title = r.get('title', 'Untitled')
        url = r.get('url', '')
        datasource = r.get('datasource', 'Unknown')
        datasources_found.add(datasource)
        
        # Handle both llmContent (string) and snippets (array) formats
        content = r.get('snippets', [])
        snippet_text = ''
        if content:
            if isinstance(content, str):
                # llmContent is a string
                snippet_text = content
            elif isinstance(content, list):
                # snippets is an array
                first = content[0] if content else None
                if first:
                    if isinstance(first, dict):
                        snippet_text = first.get('text', first.get('snippet', ''))
                    elif isinstance(first, str):
                        snippet_text = first
        
        author = r.get('author', '')
        updated = r.get('updatedAt', '')[:10] if r.get('updatedAt') else ''
        
        # Emphasize datasource for verification
        entry = f"**[{i}] {title}**"
        entry += f"\n- **Datasource: {datasource}**"  # Bold to verify filtering
        if updated:
            entry += f" | Updated: {updated}"
        if author:
            entry += f" | Author: {author}"
        if snippet_text:
            snippet_text = snippet_text[:500] + "..." if len(snippet_text) > 500 else snippet_text
            entry += f"\n- Content: {snippet_text}"
        entry += f"\n- URL: {url}"
        formatted.append(entry)
    
    # Add header showing which datasources were returned
    header = f"Found {len(results)} result(s) from {source_name}\n"
    header += f"[Datasources in results: {', '.join(sorted(datasources_found))}]\n\n"
    
    return header + "\n\n---\n\n".join(formatted)


# =============================================================================
# TOOLS - Using Glean's proper facetFilters API
# =============================================================================
# Based on Glean API docs: https://developers.glean.com/guides/search/filtering-results
# 
# Available facetFilters:
#   - type: document type (opportunity, account, contact, etc.)
#   - from: author/owner
#   - last_updated_at: date range
#   - collection, has, my
#
# NOTE: There is NO facet filter for account name. Glean uses semantic search,
# so account name filtering happens via the query string, not filters.
# The datasourcesFilter restricts to specific apps (salescloud, gong, etc.)

def search_salesforce_opportunities(query: str) -> str:
    """
    Search Salesforce for OPPORTUNITIES (renewals, contracts, deals).
    Use this for: renewal dates, contract terms, deal stages, close dates.
    
    The query should include the account/company name prominently.
    Example: "AdventHealth renewal" or "Target contract close date"
    """
    # Add type filter via facetFilters for opportunities only
    facet_filters = [
        {"fieldName": "type", "values": [{"value": "opportunity", "relationType": "EQUALS"}]}
    ]
    results = glean_search(query, datasources=["salescloud"], num_results=5, facet_filters=facet_filters)
    return format_results(results, "Salesforce Opportunities")


def search_salesforce_accounts(query: str) -> str:
    """
    Search Salesforce for ACCOUNT records (company info, account details).
    Use this for: account overview, company information, account health.
    
    The query should include the account/company name prominently.
    Example: "AdventHealth account" or "Target company overview"
    """
    # Add type filter for accounts only
    facet_filters = [
        {"fieldName": "type", "values": [{"value": "account", "relationType": "EQUALS"}]}
    ]
    results = glean_search(query, datasources=["salescloud"], num_results=5, facet_filters=facet_filters)
    return format_results(results, "Salesforce Accounts")


def search_salesforce_contacts(query: str) -> str:
    """
    Search Salesforce for CONTACTS (people, stakeholders, decision makers).
    Use this for: key contacts, decision makers, stakeholders, executives.
    
    The query should include the account/company name prominently.
    Example: "AdventHealth contacts" or "Target decision makers"
    """
    # Add type filter for contacts only
    facet_filters = [
        {"fieldName": "type", "values": [{"value": "contact", "relationType": "EQUALS"}]}
    ]
    results = glean_search(query, datasources=["salescloud"], num_results=5, facet_filters=facet_filters)
    return format_results(results, "Salesforce Contacts")


def search_metrics_and_dashboards(query: str) -> str:
    """
    Search Salesforce and Looker for metrics, dashboards, funding caps, spend.
    Use this for: funding caps, YTD spend, enrollments, utilization dashboards.
    
    The query should include the account/company name prominently.
    Example: "JPMC annual funding cap" or "AdventHealth enrollment dashboard"
    """
    results = glean_search(query, datasources=["salescloud", "looker"], num_results=6)
    return format_results(results, "Metrics (Salesforce + Looker)")


def search_strategy_docs(query: str) -> str:
    """
    Search Google Drive for QBRs, Account Plans, strategy docs, presentations.
    Use this for: account strategy, QBR decks, business reviews, planning docs.
    
    The query should include the account/company name prominently.
    Example: "AdventHealth QBR" or "Target account plan 2025"
    """
    results = glean_search(query, datasources=["gdrive"], num_results=5)
    return format_results(results, "Google Drive")


def search_communications(query: str) -> str:
    """
    Search Gong, Slack, Gmail for calls, messages, and communications.
    Use this for: call sentiment, recent meetings, email threads, Slack discussions.
    
    The query should include the account/company name prominently.
    Example: "AdventHealth recent call" or "JPMC meeting sentiment"
    """
    results = glean_search(query, datasources=["gong", "slack", "gmail"], num_results=9)
    return format_results(results, "Communications (Gong/Slack/Gmail)")


def search_general_fallback(query: str) -> str:
    """
    Search ALL sources without any datasource filtering.
    Use this as a last resort when other tools don't find relevant results.
    Only use when user explicitly approves searching all sources.
    """
    results = glean_search(query, datasources=None, num_results=10)
    return format_results(results, "All Sources")


TOOLS = {
    "search_salesforce_opportunities": search_salesforce_opportunities,
    "search_salesforce_accounts": search_salesforce_accounts,
    "search_salesforce_contacts": search_salesforce_contacts,
    "search_metrics_and_dashboards": search_metrics_and_dashboards,
    "search_strategy_docs": search_strategy_docs,
    "search_communications": search_communications,
    "search_general_fallback": search_general_fallback,
}

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_salesforce_opportunities",
            "description": "Search Salesforce OPPORTUNITIES for renewals, contracts, deals, close dates. Query MUST start with the account name. Example: 'AdventHealth renewal date' or 'Target contract'",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Query starting with account name, e.g., 'AdventHealth renewal'"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_salesforce_accounts",
            "description": "Search Salesforce ACCOUNT records for company info, account overview. Query MUST start with the account name. Example: 'AdventHealth account overview'",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Query starting with account name, e.g., 'JPMC account'"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_salesforce_contacts",
            "description": "Search Salesforce CONTACTS for decision makers, stakeholders, executives. Query MUST start with the account name. Example: 'AdventHealth contacts' or 'Target decision makers'",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Query starting with account name, e.g., 'AdventHealth contacts'"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_metrics_and_dashboards",
            "description": "Search Salesforce and Looker for funding caps, spend, enrollments, dashboards. Query should include account name.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Query with account name, e.g., 'JPMC funding cap'"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_strategy_docs",
            "description": "Search Google Drive for QBRs, Account Plans, strategy documents. Query should include account name.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Query with account name, e.g., 'AdventHealth QBR'"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_communications",
            "description": "Search Gong, Slack, Gmail for calls, sentiment, messages. Query should include account name.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Query with account name, e.g., 'AdventHealth recent call'"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_general_fallback",
            "description": "Search ALL sources without filtering. Only use when user explicitly approves fallback after other tools fail.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"]
            }
        }
    },
]


# =============================================================================
# AGENT
# =============================================================================

class EPSAgentCLI:
    """Simple CLI agent using OpenAI Responses pattern."""
    
    def __init__(self):
        self.client = OpenAI()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    def execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool and return the result."""
        if name not in TOOLS:
            return f"Unknown tool: {name}"
        
        # Show tool call with args
        console.print(f"\n  [bold cyan]🔧 {name}[/bold cyan]")
        console.print(f"  [dim]   Query: \"{args.get('query', '')}\"[/dim]")
        
        result = TOOLS[name](**args)
        
        # Show snippet of results
        lines = result.split('\n')
        preview_lines = lines[:8]  # Show first 8 lines
        preview = '\n'.join(preview_lines)
        if len(lines) > 8:
            preview += f"\n  ... ({len(lines) - 8} more lines)"
        
        console.print(Panel(
            preview,
            title=f"[dim]Tool Results[/dim]",
            border_style="dim",
            padding=(0, 1)
        ))
        
        return result
    
    def chat(self, user_message: str) -> str:
        """Process a user message and return the response."""
        self.messages.append({"role": "user", "content": user_message})
        
        max_iterations = 10
        iteration = 0
        
        for iteration in range(max_iterations):
            # Call the LLM
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=self.messages,
                tools=TOOL_SPECS,
            )
            
            assistant_message = response.choices[0].message
            
            # Show thinking/reasoning if present (before tool calls)
            if assistant_message.content and assistant_message.tool_calls:
                console.print(f"\n[bold yellow]💭 Thinking:[/bold yellow]")
                console.print(f"[dim]{assistant_message.content}[/dim]")
            
            # If no tool calls, we're done
            if not assistant_message.tool_calls:
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_message.content
                })
                if iteration > 0:
                    console.print(f"\n[dim]✓ Completed after {iteration + 1} LLM call(s)[/dim]")
                return assistant_message.content
            
            # Show which tools will be called
            tool_names = [tc.function.name for tc in assistant_message.tool_calls]
            console.print(f"\n[dim]📋 Planning to call: {', '.join(tool_names)}[/dim]")
            
            # Execute tool calls
            self.messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            for tool_call in assistant_message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = self.execute_tool(tool_call.function.name, args)
                
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        
        return "Max iterations reached. Please try a more specific query."
    
    def reset(self):
        """Reset conversation history."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        console.print("[dim]Conversation reset.[/dim]")


def main():
    """Main CLI loop."""
    global _glean_api_token, _glean_instance
    
    # Load credentials
    _glean_api_token = os.environ.get("GLEAN_API_TOKEN")
    _glean_instance = os.environ.get("GLEAN_INSTANCE")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    # Check credentials
    missing = []
    if not _glean_api_token:
        missing.append("GLEAN_API_TOKEN")
    if not _glean_instance:
        missing.append("GLEAN_INSTANCE")
    if not openai_key:
        missing.append("OPENAI_API_KEY")
    
    if missing:
        console.print(f"[red]❌ Missing environment variables: {missing}[/red]")
        console.print("\nSet them in your .env file or environment.")
        sys.exit(1)
    
    # Resolve Glean instance for display
    glean_display = _glean_instance
    if "." not in _glean_instance:
        glean_display = f"{_glean_instance}-be.glean.com"
    
    # Print header
    console.print(Panel.fit(
        "[bold cyan]EPS Account Intelligence Agent[/bold cyan]\n"
        "[dim]OpenAI Responses Pattern - CLI Version[/dim]\n\n"
        f"Model: {LLM_MODEL}\n"
        f"Glean: {glean_display}\n\n"
        "[dim]Commands: 'quit' to exit, 'reset' to clear history[/dim]",
        title="🤖 EPS Agent",
        border_style="cyan"
    ))
    
    # Test Glean connection
    console.print("\n[dim]Testing Glean connection...[/dim]")
    test_results = glean_search("test", num_results=1)
    if test_results and not test_results[0].get("error"):
        console.print("[green]✓ Glean connected![/green]\n")
    else:
        console.print(f"[yellow]⚠️ Glean test: {test_results}[/yellow]\n")
    
    # Create agent
    agent = EPSAgentCLI()
    
    # Main loop
    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                console.print("[dim]Goodbye![/dim]")
                break
            
            if user_input.lower() == "reset":
                agent.reset()
                continue
            
            console.print()
            
            with console.status("[bold cyan]Thinking...[/bold cyan]"):
                response = agent.chat(user_input)
            
            console.print("\n[bold blue]Agent:[/bold blue]")
            console.print(Markdown(response))
            
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()

