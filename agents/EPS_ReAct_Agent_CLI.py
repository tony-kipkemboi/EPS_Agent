import asyncio
import os
import json
import sys
from typing import List, Dict, Any
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Import our custom tools
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from tools.EPS_MCP_Tools import EPSVirtualTools

# Try importing rich for pretty output
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.status import Status
    from rich.syntax import Syntax
    from rich.tree import Tree
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    print("Warning: 'rich' library not found. Installing recommended for better UI.")
    HAS_RICH = False

load_dotenv()

# Configuration
GLEAN_SERVER_URL = "https://guild-be.glean.com/mcp/aia"
OPENAI_MODEL = "gpt-4o"

SYSTEM_PROMPT = """
You are the EPS Account Intelligence Agent. 
Your goal is to help Account Managers (AMs) retrieve and synthesize account information strictly following the "Source of Truth" rules.

### DATA SOURCE RULES (CRITICAL):
1. **Dates, Contracts, Contacts:** You MUST use `search_salesforce`.
2. **Risk / Health:** If asked about health or risks, you MUST use `search_salesforce` (checking for 'Risk' fields) AND `search_communications` (for sentiment).
3. **Funding, Spend, Enrollments:** You MUST use `search_metrics_and_dashboards`.
4. **Strategy, QBRs, Plans:** You MUST use `search_strategy_docs`.
5. **Emails:** If asked about emails or recent comms from specific people/accounts (e.g. JPMC), use `search_communications` (which covers Gmail).
6. **Deep Reading:** If a user asks for details *inside* a document found by search, use `read_full_document`.

### FALLBACK PROTOCOL:
If a specific tool returns NO results (e.g., "No strategy docs found"):
1. Do NOT hallucinate.
2. Do NOT automatically call the fallback tool.
3. **ASK THE USER** for permission: "I couldn't find this in [Source]. Would you like me to search all sources?"
4. **ONLY** if the user says "Yes" or "Search all", call `search_general_fallback`.

### CITATION FORMAT (CRITICAL):
Every factual claim in your final answer MUST be cited.
Format: `[Source: Document Title (Author, Date) - https://full.link.here]`
**IMPORTANT:** You MUST include the actual clickable URL found in the search result. Do not omit it.

### PROCESS:
1. **THOUGHT:** Analyze intent. Select specific tool.
2. **TOOL CALL:** Call the tool.
3. **OBSERVATION:** Check if results exist.
4. **FINAL ANSWER:** If results exist -> Synthesize. If NO results -> Ask for fallback permission.
"""

def print_agent_msg(content: str):
    if HAS_RICH:
        console.print(Panel(Markdown(content), title="[bold green]EPS Agent[/bold green]", border_style="green"))
    else:
        print(f"\n[EPS Agent]: {content}")

def print_tool_use(tool_name: str, args: Dict):
    if HAS_RICH:
        # Create a neat table or syntax block for arguments
        arg_str = json.dumps(args, indent=2)
        console.print(f"\n[dim]╭─ 🔨 [bold]{tool_name}[/bold] ───────────────────────────────────────────╮[/dim]")
        console.print(f"[dim]│ Arguments: {arg_str.replace('{', '').replace('}', '').strip()}                               │[/dim]")
        console.print(f"[dim]╰───────────────────────────────────────────────────────────────╯[/dim]")
    else:
        print(f"🔨 Calling Tool: {tool_name} with {args}")

def print_tool_result(result: str):
    if HAS_RICH:
        # Truncate result for display
        preview = result[:200].replace("\n", " ") + "..." if len(result) > 200 else result
        console.print(f"[dim]   ↳ Result: {preview}[/dim]\n")
    else:
        print(f"   Result: {result[:100]}...")

async def run_chat_session():
    api_token = os.environ.get("GLEAN_API_TOKEN")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_token or not openai_key:
        print("Error: Missing GLEAN_API_TOKEN or OPENAI_API_KEY")
        return

    client = AsyncOpenAI(api_key=openai_key)
    headers = {"Authorization": f"Bearer {api_token}"}
    
    if HAS_RICH:
        console.rule("[bold blue]EPS Account Intelligence Agent (MVP)[/bold blue]")
        console.print("Type [bold red]exit[/bold red] to quit.\n")

    async with AsyncExitStack() as stack:
        if HAS_RICH:
            status = console.status("[bold green]Connecting to Glean...[/bold green]")
            status.start()
            
        try:
            read, write, _ = await stack.enter_async_context(
                streamablehttp_client(GLEAN_SERVER_URL, headers=headers)
            )
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            tools = EPSVirtualTools(session)
            if HAS_RICH: 
                status.stop()
                console.print("[bold green]✓ Connected.[/bold green]")
        except Exception as e:
            if HAS_RICH: status.stop()
            print(f"Connection failed: {e}")
            return

        # Tool Definitions
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_salesforce",
                    "description": "Search Salesforce for factual account data: dates, contacts, risk.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_metrics_and_dashboards",
                    "description": "Search for funding caps, spend, enrollments.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_strategy_docs",
                    "description": "Search Google Drive for QBRs and strategy docs.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_communications",
                    "description": "Search Gong, Slack, Gmail for sentiment and recent emails/chatter.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_general_fallback",
                    "description": "Search ALL sources. Use ONLY if user grants permission after a failed specific search.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_full_document",
                    "description": "Read full text of a document URL.",
                    "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
                }
            }
        ]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        while True:
            if HAS_RICH:
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            else:
                user_input = input("\nYou: ")

            if user_input.lower() in ["exit", "quit", "q"]:
                break
            
            messages.append({"role": "user", "content": user_input})

            # --- REASONING LOOP ---
            for step in range(5):
                if HAS_RICH:
                    step_status = console.status("[italic]Thinking...[/italic]")
                    step_status.start()

                try:
                    response = await client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=messages,
                        tools=openai_tools,
                        tool_choice="auto"
                    )
                    msg = response.choices[0].message
                    messages.append(msg)
                    
                    if HAS_RICH: step_status.stop()

                    if msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            fn_name = tool_call.function.name
                            args = json.loads(tool_call.function.arguments)
                            
                            print_tool_use(fn_name, args)
                            
                            # Execute Tool
                            if HAS_RICH: 
                                exec_status = console.status(f"[dim]Executing {fn_name}...[/dim]")
                                exec_status.start()

                            if fn_name == "search_salesforce":
                                result = await tools.search_salesforce(args["query"])
                            elif fn_name == "search_metrics_and_dashboards":
                                result = await tools.search_metrics_and_dashboards(args["query"])
                            elif fn_name == "search_strategy_docs":
                                result = await tools.search_strategy_docs(args["query"])
                            elif fn_name == "search_communications":
                                result = await tools.search_communications(args["query"])
                            elif fn_name == "search_general_fallback":
                                result = await tools.search_general_fallback(args["query"])
                            elif fn_name == "read_full_document":
                                result = await tools.read_full_document(args["url"])
                            else:
                                result = "Error: Unknown tool."

                            if HAS_RICH: exec_status.stop()
                            
                            print_tool_result(str(result))

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": str(result)
                            })
                    else:
                        print_agent_msg(msg.content)
                        break 
                except Exception as e:
                    if HAS_RICH: step_status.stop()
                    print(f"Error in agent loop: {e}")
                    break

if __name__ == "__main__":
    try:
        asyncio.run(run_chat_session())
    except KeyboardInterrupt:
        print("\nGoodbye!")
