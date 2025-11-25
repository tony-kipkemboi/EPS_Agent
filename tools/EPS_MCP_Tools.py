import logging
from typing import Dict, Any, List, Optional
from mcp import ClientSession

# Configure logging
logger = logging.getLogger(__name__)

class EPSVirtualTools:
    """
    Virtual Tools wrapper for the EPS Account Intelligence Agent.
    Enforces PRD-defined source prioritization and data hygiene.
    """

    def __init__(self, session: ClientSession):
        self.session = session

    async def _mcp_search(self, query: str, app_filter: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Internal helper to execute a filtered search via the AIA MCP Server.
        """
        # Only append app_filter if it's provided
        full_query = f"{query} {app_filter} num_results:{num_results}" if app_filter else f"{query} num_results:{num_results}"
        logger.info(f"Executing MCP Search: {full_query}")
        
        try:
            result = await self.session.call_tool("search", arguments={"query": full_query})
            return result.content
        except Exception as e:
            logger.error(f"Search failed for {full_query}: {e}")
            return []

    async def _mcp_read(self, url: str) -> str:
        """
        Internal helper to read full document content.
        """
        logger.info(f"Reading Document: {url}")
        try:
            result = await self.session.call_tool("read_document", arguments={"url": url})
            # Return the first text content block
            return result.content[0].text if result.content else "No content found."
        except Exception as e:
            logger.error(f"Read failed for {url}: {e}")
            return f"Error reading document: {e}"

    # --- LEVEL 1: BASIC RETRIEVAL (SALESFORCE) ---
    
    async def search_salesforce(self, query: str) -> str:
        """
        Strictly for factual account data: dates, contracts, contacts, risk.
        Source of Truth: Salesforce.
        """
        logger.info(f"Tool Call: search_salesforce('{query}')")
        results = await self._mcp_search(query, "app:salesforce", num_results=5)
        return f"--- SALESFORCE RESULTS FOR '{query}' ---\n{results[0].text if results else 'No Salesforce records found.'}"

    # --- LEVEL 2: QUANTITATIVE / LOOKER ---

    async def search_metrics_and_dashboards(self, query: str) -> str:
        """
        For funding caps, spend, enrollments, and funnel metrics.
        Prioritizes Salesforce (Budget tab) then Looker (Dashboards).
        """
        logger.info(f"Tool Call: search_metrics_and_dashboards('{query}')")
        
        # 1. Try Salesforce first
        sf_results = await self._mcp_search(query, "app:salesforce", num_results=3)
        
        # 2. Try Looker for dashboard links
        looker_results = await self._mcp_search(query, "app:looker", num_results=3)
        
        combined_output = f"--- METRICS SOURCES FOR '{query}' ---\n"
        combined_output += f"[Salesforce Data]:\n{sf_results[0].text if sf_results else 'None'}\n\n"
        combined_output += f"[Looker Dashboards]:\n{looker_results[0].text if looker_results else 'None'}"
        
        return combined_output

    # --- LEVEL 3: STRATEGIC SYNTHESIS ---

    async def search_strategy_docs(self, query: str) -> str:
        """
        For QBRs, Account Plans, and long-form strategy documents.
        Source: Google Drive.
        """
        logger.info(f"Tool Call: search_strategy_docs('{query}')")
        results = await self._mcp_search(query, "app:googledrive", num_results=5)
        return f"--- STRATEGY DOCS FOR '{query}' ---\n{results[0].text if results else 'No strategy docs found.'}"

    async def search_communications(self, query: str) -> str:
        """
        For sentiment, voice of customer, and team chatter.
        Sources: Gong, Slack, Gmail.
        """
        logger.info(f"Tool Call: search_communications('{query}')")
        
        # Parallel execution (simulated sequentially for MVP safety)
        gong_results = await self._mcp_search(query, "app:gong", num_results=3)
        slack_results = await self._mcp_search(query, "app:slack", num_results=3)
        gmail_results = await self._mcp_search(query, "app:gmail", num_results=3)
        
        combined_output = f"--- COMMUNICATION SOURCES FOR '{query}' ---\n"
        combined_output += f"[Gong Calls]:\n{gong_results[0].text if gong_results else 'None'}\n\n"
        combined_output += f"[Slack Threads]:\n{slack_results[0].text if slack_results else 'None'}\n\n"
        combined_output += f"[Gmail Threads]:\n{gmail_results[0].text if gmail_results else 'None'}"
        
        return combined_output

    async def read_full_document(self, url: str) -> str:
        """
        Reads the full content of a specific document URL found via search.
        """
        logger.info(f"Tool Call: read_full_document('{url}')")
        content = await self._mcp_read(url)
        return f"--- DOCUMENT CONTENT FOR '{url}' ---\n{content}"

    # --- FALLBACK ---
    
    async def search_general_fallback(self, query: str) -> str:
        """
        Unrestricted search across ALL sources. 
        Use ONLY if specific tools fail and user permission is granted.
        """
        logger.info(f"Tool Call: search_general_fallback('{query}')")
        results = await self._mcp_search(query, "", num_results=5)
        return f"--- GENERAL SEARCH RESULTS FOR '{query}' ---\n{results[0].text if results else 'No results found in any source.'}"
