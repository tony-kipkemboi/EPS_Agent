"""
Tool Lab - Testing and Fine-tuning Glean Search Tools
======================================================

Run this file to test and iterate on tool functions.
Each tool can be tested independently to see raw results.

Usage:
    python tool_lab.py

Or in Python:
    from tool_lab import test_salesforce_opportunities
    test_salesforce_opportunities("AdventHealth renewal")
"""

import json
import os
from typing import Optional
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

GLEAN_API_TOKEN = os.environ.get("GLEAN_API_TOKEN")
GLEAN_INSTANCE = os.environ.get("GLEAN_INSTANCE")


# =============================================================================
# GLEAN API CORE
# =============================================================================

def get_glean_api_url() -> str:
    """Get the Glean API URL."""
    if not GLEAN_INSTANCE:
        raise RuntimeError("GLEAN_INSTANCE not set")
    
    clean = GLEAN_INSTANCE.replace("https://", "").replace("http://", "").rstrip("/")
    if "." not in clean:
        clean = f"{clean}-be.glean.com"
    
    return f"https://{clean}/rest/api/v1/search"


def glean_search_raw(
    query: str,
    datasources: Optional[list[str]] = None,
    num_results: int = 10,
    facet_filters: Optional[list[dict]] = None,
    debug: bool = True
) -> dict:
    """
    Raw Glean search - returns full API response for debugging.
    """
    if not GLEAN_API_TOKEN:
        raise RuntimeError("GLEAN_API_TOKEN not set")
    
    headers = {"Authorization": f"Bearer {GLEAN_API_TOKEN}"}
    
    request_options = {
        "facetBucketSize": 100,
        "returnLlmContentOverSnippets": True,
    }
    
    if datasources:
        request_options["datasourcesFilter"] = datasources
    
    if facet_filters:
        request_options["facetFilters"] = facet_filters
    
    payload = {
        "query": query,
        "pageSize": num_results,
        "maxSnippetSize": 4000,
        "requestOptions": request_options
    }
    
    if debug:
        print("\n" + "="*60)
        print("GLEAN API REQUEST")
        print("="*60)
        print(f"URL: {get_glean_api_url()}")
        print(f"Query: {query}")
        print(f"Datasources: {datasources}")
        print(f"Facet Filters: {json.dumps(facet_filters, indent=2) if facet_filters else 'None'}")
        print("="*60 + "\n")
    
    with httpx.Client(timeout=30.0) as client:
        response = client.post(get_glean_api_url(), headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


# =============================================================================
# RESULT FORMATTING
# =============================================================================

def format_result_simple(result: dict, index: int) -> str:
    """Format a single result for display."""
    doc = result.get("document", {})
    title = doc.get("title", "Untitled")
    url = doc.get("url", "")
    datasource = doc.get("datasource", "Unknown")
    
    # Get content
    content = result.get("llmContent") or result.get("snippets", [])
    if isinstance(content, list) and content:
        if isinstance(content[0], dict):
            content_text = content[0].get("text", content[0].get("snippet", ""))[:200]
        else:
            content_text = str(content[0])[:200]
    elif isinstance(content, str):
        content_text = content[:200]
    else:
        content_text = ""
    
    return f"""
[{index}] {title}
    Source: {datasource}
    URL: {url}
    Preview: {content_text}...
"""


def analyze_results(results: list[dict], target_account: str = None) -> None:
    """Analyze results for relevance."""
    print("\n" + "="*60)
    print("RESULTS ANALYSIS")
    print("="*60)
    
    if not results:
        print("❌ No results found")
        return
    
    print(f"Total results: {len(results)}")
    
    # Check if target account is in results
    if target_account:
        matching = 0
        non_matching = []
        
        for r in results:
            doc = r.get("document", {})
            title = doc.get("title", "").lower()
            
            if target_account.lower() in title:
                matching += 1
            else:
                non_matching.append(doc.get("title", "Untitled"))
        
        print(f"\n✅ Results matching '{target_account}': {matching}/{len(results)}")
        
        if non_matching:
            print(f"⚠️  Non-matching results:")
            for title in non_matching[:5]:
                print(f"   - {title}")
    
    # Show datasource breakdown
    datasources = {}
    for r in results:
        ds = r.get("document", {}).get("datasource", "unknown")
        datasources[ds] = datasources.get(ds, 0) + 1
    
    print(f"\nDatasource breakdown:")
    for ds, count in datasources.items():
        print(f"   {ds}: {count}")


# =============================================================================
# QUERY OPTIMIZATION
# =============================================================================

def quote_account_name(query: str) -> str:
    """
    Quote the account name in a query to prevent Glean from returning unrelated results.
    
    Assumes account name is at the START of the query.
    """
    if query.startswith('"'):
        return query
    
    action_words = [
        'renewal', 'renew', 'contract', 'opportunity', 'deal',
        'contact', 'contacts', 'stakeholder', 'decision',
        'account', 'company', 'info', 'overview',
        'call', 'calls', 'meeting', 'email', 'slack',
        'qbr', 'ebr', 'plan', 'strategy', 'doc',
        'metric', 'metrics', 'dashboard', 'spend', 'funding',
        'key', 'recent', 'last', 'latest', 'upcoming'
    ]
    
    words = query.split()
    account_words = []
    rest_words = []
    found_action = False
    
    for word in words:
        if not found_action and word.lower() not in action_words:
            account_words.append(word)
        else:
            found_action = True
            rest_words.append(word)
    
    if account_words:
        account_name = ' '.join(account_words)
        rest = ' '.join(rest_words)
        return f'"{account_name}" {rest}'.strip()
    
    return query


# =============================================================================
# TOOL FUNCTIONS TO TEST
# =============================================================================

def test_salesforce_opportunities(query: str, target_account: str = None, use_auto_quote: bool = True) -> None:
    """
    Test Salesforce Opportunities search.
    
    Goal: Only return OPPORTUNITIES for the specified account.
    """
    print("\n" + "🔍 TESTING: search_salesforce_opportunities")
    
    # Apply auto-quoting if enabled
    if use_auto_quote:
        optimized_query = quote_account_name(query)
        if optimized_query != query:
            print(f"   📝 Auto-quoted: {query} → {optimized_query}")
        query = optimized_query
    
    facet_filters = [
        {"fieldName": "type", "values": [{"value": "opportunity", "relationType": "EQUALS"}]}
    ]
    
    response = glean_search_raw(
        query=query,
        datasources=["salescloud"],
        num_results=5,
        facet_filters=facet_filters
    )
    
    results = response.get("results", [])
    
    print("\nRESULTS:")
    for i, r in enumerate(results, 1):
        print(format_result_simple(r, i))
    
    analyze_results(results, target_account or query.split()[0])


def test_salesforce_accounts(query: str, target_account: str = None) -> None:
    """Test Salesforce Accounts search."""
    print("\n" + "🔍 TESTING: search_salesforce_accounts")
    
    facet_filters = [
        {"fieldName": "type", "values": [{"value": "account", "relationType": "EQUALS"}]}
    ]
    
    response = glean_search_raw(
        query=query,
        datasources=["salescloud"],
        num_results=5,
        facet_filters=facet_filters
    )
    
    results = response.get("results", [])
    
    print("\nRESULTS:")
    for i, r in enumerate(results, 1):
        print(format_result_simple(r, i))
    
    analyze_results(results, target_account or query.split()[0])


def test_salesforce_contacts(query: str, target_account: str = None) -> None:
    """Test Salesforce Contacts search."""
    print("\n" + "🔍 TESTING: search_salesforce_contacts")
    
    facet_filters = [
        {"fieldName": "type", "values": [{"value": "contact", "relationType": "EQUALS"}]}
    ]
    
    response = glean_search_raw(
        query=query,
        datasources=["salescloud"],
        num_results=5,
        facet_filters=facet_filters
    )
    
    results = response.get("results", [])
    
    print("\nRESULTS:")
    for i, r in enumerate(results, 1):
        print(format_result_simple(r, i))
    
    analyze_results(results, target_account or query.split()[0])


def test_communications(query: str, target_account: str = None) -> None:
    """Test Communications search (Gong, Slack, Gmail)."""
    print("\n" + "🔍 TESTING: search_communications")
    
    response = glean_search_raw(
        query=query,
        datasources=["gong", "slack", "gmail"],
        num_results=9
    )
    
    results = response.get("results", [])
    
    print("\nRESULTS:")
    for i, r in enumerate(results, 1):
        print(format_result_simple(r, i))
    
    analyze_results(results, target_account or query.split()[0])


def test_strategy_docs(query: str, target_account: str = None) -> None:
    """Test Strategy Docs search (Google Drive)."""
    print("\n" + "🔍 TESTING: search_strategy_docs")
    
    response = glean_search_raw(
        query=query,
        datasources=["gdrive"],
        num_results=5
    )
    
    results = response.get("results", [])
    
    print("\nRESULTS:")
    for i, r in enumerate(results, 1):
        print(format_result_simple(r, i))
    
    analyze_results(results, target_account or query.split()[0])


def test_metrics(query: str, target_account: str = None) -> None:
    """Test Metrics search (Salesforce + Looker)."""
    print("\n" + "🔍 TESTING: search_metrics_and_dashboards")
    
    response = glean_search_raw(
        query=query,
        datasources=["salescloud", "looker"],
        num_results=6
    )
    
    results = response.get("results", [])
    
    print("\nRESULTS:")
    for i, r in enumerate(results, 1):
        print(format_result_simple(r, i))
    
    analyze_results(results, target_account or query.split()[0])


# =============================================================================
# EXPERIMENTAL: STRICTER FILTERING
# =============================================================================

def test_strict_opportunity_search(account_name: str) -> None:
    """
    EXPERIMENTAL: Try stricter filtering for opportunities.
    
    Test different query patterns to get ONLY the target account's opportunities.
    """
    print(f"\n🧪 EXPERIMENTAL: Strict opportunity search for '{account_name}'")
    
    # Test 1: Quoted account name
    print("\n--- Test 1: Quoted account name ---")
    test_salesforce_opportunities(f'"{account_name}" renewal', account_name)
    
    # Test 2: Account name + type filter
    print("\n--- Test 2: Account first, then action ---")
    test_salesforce_opportunities(f'{account_name} renewal date', account_name)
    
    # Test 3: Just account name
    print("\n--- Test 3: Just account name ---")
    test_salesforce_opportunities(account_name, account_name)


def test_with_post_filtering(query: str, account_name: str) -> None:
    """
    EXPERIMENTAL: Test with post-result filtering.
    
    After getting results, filter to only those containing the account name.
    """
    print(f"\n🧪 EXPERIMENTAL: Post-filtering for '{account_name}'")
    
    facet_filters = [
        {"fieldName": "type", "values": [{"value": "opportunity", "relationType": "EQUALS"}]}
    ]
    
    response = glean_search_raw(
        query=query,
        datasources=["salescloud"],
        num_results=10,  # Get more, filter down
        facet_filters=facet_filters
    )
    
    results = response.get("results", [])
    
    # Post-filter: only keep results with account name in title
    filtered = []
    rejected = []
    
    for r in results:
        doc = r.get("document", {})
        title = doc.get("title", "").lower()
        content = str(r.get("llmContent", "")).lower() + str(r.get("snippets", "")).lower()
        
        if account_name.lower() in title or account_name.lower() in content:
            filtered.append(r)
        else:
            rejected.append(doc.get("title", "Untitled"))
    
    print(f"\n📊 POST-FILTER RESULTS:")
    print(f"   Original: {len(results)} results")
    print(f"   Filtered: {len(filtered)} results")
    print(f"   Rejected: {len(rejected)} results")
    
    if rejected:
        print(f"\n   ❌ Rejected (no '{account_name}' in title/content):")
        for title in rejected[:5]:
            print(f"      - {title}")
    
    print(f"\n   ✅ Kept:")
    for i, r in enumerate(filtered[:5], 1):
        doc = r.get("document", {})
        print(f"      [{i}] {doc.get('title', 'Untitled')}")


def test_quoted_jpmc() -> None:
    """Test if quoting JPMC helps with filtering."""
    print("\n" + "="*60)
    print("TEST: Quoted JPMC vs Unquoted")
    print("="*60)
    
    print("\n--- Unquoted (no auto-quote) ---")
    test_salesforce_opportunities("JPMorgan Chase renewal", "JPMorgan", use_auto_quote=False)
    
    print("\n--- With Auto-Quote ---")
    test_salesforce_opportunities("JPMorgan Chase renewal", "JPMorgan", use_auto_quote=True)


def test_auto_quoting() -> None:
    """Test the automatic quoting function."""
    print("\n" + "="*60)
    print("TEST: Auto-quoting function")
    print("="*60)
    
    test_cases = [
        "JPMorgan Chase renewal",
        "AdventHealth key contacts",
        "Target renewal date",
        "Kaiser Permanente recent calls",
        '"Already Quoted" renewal',
    ]
    
    for query in test_cases:
        result = quote_account_name(query)
        print(f"  {query:40} → {result}")


def inspect_full_response(query: str, datasource: str = "salescloud") -> None:
    """
    Inspect the FULL Glean API response to find permission-related fields.
    
    This helps discover:
    - hasMoreResults
    - restrictedResults / filteredResults
    - Permission-denied indicators
    - Any other metadata about access
    """
    print(f"\n🔬 INSPECTING FULL RESPONSE STRUCTURE")
    print("="*60)
    
    facet_filters = [
        {"fieldName": "type", "values": [{"value": "opportunity", "relationType": "EQUALS"}]}
    ]
    
    response = glean_search_raw(
        query=query,
        datasources=[datasource],
        num_results=3,
        facet_filters=facet_filters,
        debug=False
    )
    
    # Print all top-level keys
    print(f"\n📋 TOP-LEVEL RESPONSE KEYS:")
    for key in response.keys():
        value = response[key]
        if isinstance(value, list):
            print(f"   {key}: list[{len(value)}]")
        elif isinstance(value, dict):
            print(f"   {key}: dict with keys {list(value.keys())[:5]}")
        else:
            print(f"   {key}: {type(value).__name__} = {str(value)[:50]}")
    
    # Check for permission-related fields
    permission_fields = [
        'hasMoreResults', 'restrictedResults', 'filteredResults',
        'accessDenied', 'permissionDenied', 'hiddenResults',
        'totalResults', 'estimatedTotalResults', 'filteredCount',
        'metadata', 'searchMetadata', 'debugInfo'
    ]
    
    print(f"\n🔐 PERMISSION-RELATED FIELDS:")
    for field in permission_fields:
        if field in response:
            print(f"   ✅ {field}: {response[field]}")
        else:
            print(f"   ❌ {field}: not present")
    
    # Check results for permission indicators
    results = response.get("results", [])
    if results:
        print(f"\n📄 FIRST RESULT STRUCTURE:")
        first = results[0]
        for key in first.keys():
            value = first[key]
            if isinstance(value, dict):
                print(f"   {key}: dict with keys {list(value.keys())[:8]}")
            elif isinstance(value, list):
                print(f"   {key}: list[{len(value)}]")
            else:
                print(f"   {key}: {str(value)[:60]}")
        
        # Check document metadata
        doc = first.get("document", {})
        print(f"\n📁 DOCUMENT METADATA KEYS:")
        for key in doc.keys():
            print(f"   {key}")
        
        # Check for permission fields in document
        doc_permission_fields = [
            'permissions', 'access', 'viewPermissions', 'restricted',
            'visibility', 'accessLevel', 'userCanView'
        ]
        print(f"\n🔐 DOCUMENT PERMISSION FIELDS:")
        for field in doc_permission_fields:
            if field in doc:
                print(f"   ✅ {field}: {doc[field]}")
    
    # Print raw JSON of interesting fields
    print(f"\n📦 RAW RESPONSE (relevant sections):")
    interesting = {k: v for k, v in response.items() if k not in ['results', 'facetResults']}
    if interesting:
        print(json.dumps(interesting, indent=2, default=str)[:1000])
    else:
        print("   No additional metadata fields found")


def discover_available_facets(datasource: str = "salescloud") -> None:
    """
    Discover what facets are available for filtering.
    """
    print(f"\n🔎 Discovering facets for: {datasource}")
    
    response = glean_search_raw(
        query="*",
        datasources=[datasource],
        num_results=1,
        debug=False
    )
    
    facets = response.get("facetResults", [])
    
    print(f"\nAvailable facets ({len(facets)}):")
    for facet in facets:
        name = facet.get("sourceName", "unknown")
        buckets = facet.get("buckets", [])
        print(f"\n  {name}:")
        for bucket in buckets[:5]:
            value = bucket.get("value", {}).get("stringValue", "?")
            count = bucket.get("count", 0)
            print(f"    - {value} ({count})")
        if len(buckets) > 5:
            print(f"    ... and {len(buckets) - 5} more")


# =============================================================================
# PEOPLE SEARCH TESTING
# =============================================================================

def test_people_search(query: str = "Tracy Platt") -> None:
    """
    Test people directory search with different datasource names.
    
    Glean's people directory might use different datasource names depending
    on where the data is synced from (Workday, BambooHR, etc.).
    """
    print("\n" + "="*60)
    print(f"TESTING: People Search for '{query}'")
    print("="*60)
    
    # Common datasource names for people directories
    datasource_options = [
        "people",
        "directory", 
        "workday",
        "bamboohr",
        "okta",
        "employee",
        "employees",
    ]
    
    working_datasources = []
    
    for ds in datasource_options:
        print(f"\n--- Testing datasource: '{ds}' ---")
        try:
            response = glean_search_raw(
                query=query,
                datasources=[ds],
                num_results=3,
                debug=False
            )
            results = response.get("results", [])
            print(f"   Results: {len(results)}")
            
            if results:
                working_datasources.append(ds)
                for i, r in enumerate(results[:2], 1):
                    doc = r.get("document", {})
                    title = doc.get("title", "Untitled")
                    url = doc.get("url", "")
                    print(f"   [{i}] {title}")
                    print(f"       URL: {url[:80]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Also try without datasource filter (general search)
    print(f"\n--- Testing: No datasource filter (general) ---")
    try:
        response = glean_search_raw(
            query=query,
            datasources=None,
            num_results=5,
            debug=False
        )
        results = response.get("results", [])
        print(f"   Results: {len(results)}")
        
        # Show what datasources appear in results
        datasources_found = {}
        for r in results:
            ds = r.get("document", {}).get("datasource", "unknown")
            datasources_found[ds] = datasources_found.get(ds, 0) + 1
        
        print(f"   Datasources in results: {datasources_found}")
        
        for i, r in enumerate(results[:3], 1):
            doc = r.get("document", {})
            title = doc.get("title", "Untitled")
            ds = doc.get("datasource", "?")
            print(f"   [{i}] ({ds}) {title}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    if working_datasources:
        print(f"✅ Working datasources: {working_datasources}")
        print(f"   Recommended: Use '{working_datasources[0]}' in search_people()")
    else:
        print("❌ No dedicated people datasource found")
        print("   People data may come from Salesforce contacts or general search")


def discover_people_datasource() -> None:
    """
    Try to discover what datasources are available for people search.
    """
    print("\n" + "="*60)
    print("DISCOVERING: Available datasources in Glean")
    print("="*60)
    
    # Search for a common name to see what datasources return results
    response = glean_search_raw(
        query="*",
        datasources=None,
        num_results=1,
        debug=False
    )
    
    # Check resultTabs for available datasources
    result_tabs = response.get("resultTabs", [])
    print(f"\nAvailable result tabs/datasources:")
    for tab in result_tabs:
        tab_id = tab.get("id", "?")
        print(f"   - {tab_id}")


# =============================================================================
# MAIN - Interactive Testing
# =============================================================================

# =============================================================================
# DATE FILTERING TESTS
# =============================================================================

def test_date_filter_keywords() -> None:
    """Test Glean's special date filter keywords."""
    print("\n" + "="*60)
    print("TEST: Date Filter Keywords")
    print("="*60)
    
    keywords = ["past_day", "past_week", "past_month", "today", "yesterday"]
    
    for keyword in keywords:
        print(f"\n--- Testing: {keyword} ---")
        facet_filters = [
            {"fieldName": "last_updated_at", "values": [{"relationType": "EQUALS", "value": keyword}]}
        ]
        
        response = glean_search_raw(
            query="AdventHealth",
            datasources=["salescloud"],
            num_results=3,
            facet_filters=facet_filters,
            debug=False
        )
        
        results = response.get("results", [])
        print(f"   Results: {len(results)}")
        
        for i, r in enumerate(results[:2], 1):
            doc = r.get("document", {})
            title = doc.get("title", "Untitled")
            update_time = doc.get("updateTime", "Unknown")
            print(f"   [{i}] {title}")
            print(f"       Updated: {update_time}")


def test_date_filter_range() -> None:
    """Test Glean's date range filtering with GT/LT."""
    print("\n" + "="*60)
    print("TEST: Date Range Filter (GT/LT)")
    print("="*60)
    
    from datetime import datetime, timedelta
    
    # Last 30 days
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"\nSearching: {start_date} to {end_date}")
    
    facet_filters = [
        {
            "fieldName": "last_updated_at",
            "values": [
                {"relationType": "GT", "value": start_date},
                {"relationType": "LT", "value": end_date}
            ]
        }
    ]
    
    response = glean_search_raw(
        query="AdventHealth",
        datasources=["gong", "slack", "gmail"],
        num_results=5,
        facet_filters=facet_filters,
        debug=False
    )
    
    results = response.get("results", [])
    print(f"\nFound {len(results)} results in date range:")
    
    for i, r in enumerate(results[:5], 1):
        doc = r.get("document", {})
        title = doc.get("title", "Untitled")
        datasource = doc.get("datasource", "Unknown")
        update_time = doc.get("updateTime", "Unknown")
        print(f"\n[{i}] ({datasource}) {title}")
        print(f"    Updated: {update_time}")


def test_communications_time_filtered(account: str = "AdventHealth", days_back: int = 7) -> None:
    """Test searching recent communications with date filter."""
    print("\n" + "="*60)
    print(f"TEST: Recent Communications for {account} (last {days_back} days)")
    print("="*60)
    
    from datetime import datetime, timedelta
    
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    facet_filters = [
        {
            "fieldName": "last_updated_at",
            "values": [{"relationType": "GT", "value": start_date}]
        }
    ]
    
    response = glean_search_raw(
        query=f'"{account}" calls meetings',
        datasources=["gong", "slack", "gmail"],
        num_results=10,
        facet_filters=facet_filters,
        debug=False
    )
    
    results = response.get("results", [])
    print(f"\nFound {len(results)} communications in last {days_back} days:")
    
    for i, r in enumerate(results[:5], 1):
        doc = r.get("document", {})
        title = doc.get("title", "Untitled")
        datasource = doc.get("datasource", "Unknown")
        update_time = doc.get("updateTime", "Unknown")
        print(f"\n[{i}] ({datasource}) {title}")
        print(f"    Updated: {update_time}")
    
    if not results:
        print("   No results - try expanding the date range or check account name")


def test_nlp_vs_filter_comparison(account: str = "AdventHealth") -> None:
    """Compare results: NLP time expression vs explicit date filter."""
    print("\n" + "="*60)
    print(f"TEST: NLP vs Date Filter Comparison for {account}")
    print("="*60)
    
    from datetime import datetime, timedelta
    
    # Method 1: NLP (let Glean interpret "last week")
    print("\n--- Method 1: NLP (query contains 'last week') ---")
    response_nlp = glean_search_raw(
        query=f'"{account}" last week calls',
        datasources=["gong"],
        num_results=5,
        debug=False
    )
    nlp_results = response_nlp.get("results", [])
    print(f"Results: {len(nlp_results)}")
    for i, r in enumerate(nlp_results[:3], 1):
        doc = r.get("document", {})
        print(f"   [{i}] {doc.get('title', 'Untitled')} | Updated: {doc.get('updateTime', 'Unknown')}")
    
    # Method 2: Explicit filter (past_week keyword)
    print("\n--- Method 2: Explicit Filter (past_week) ---")
    facet_filters = [
        {"fieldName": "last_updated_at", "values": [{"relationType": "EQUALS", "value": "past_week"}]}
    ]
    response_filter = glean_search_raw(
        query=f'"{account}" calls',
        datasources=["gong"],
        num_results=5,
        facet_filters=facet_filters,
        debug=False
    )
    filter_results = response_filter.get("results", [])
    print(f"Results: {len(filter_results)}")
    for i, r in enumerate(filter_results[:3], 1):
        doc = r.get("document", {})
        print(f"   [{i}] {doc.get('title', 'Untitled')} | Updated: {doc.get('updateTime', 'Unknown')}")
    
    # Summary
    print("\n--- Summary ---")
    print(f"NLP approach: {len(nlp_results)} results")
    print(f"Filter approach: {len(filter_results)} results")
    if len(filter_results) != len(nlp_results):
        print("⚠️  Different result counts - explicit filter may be more accurate")
    else:
        print("✅ Same result count")


if __name__ == "__main__":
    print("="*60)
    print("EPS Tool Lab - Test and Fine-tune Glean Tools")
    print("="*60)
    
    # Check credentials
    if not GLEAN_API_TOKEN:
        print("❌ GLEAN_API_TOKEN not set. Add to .env file.")
        exit(1)
    
    print(f"✅ Using Glean instance: {GLEAN_INSTANCE}")
    
    # Example tests - uncomment what you want to test
    
    # Test 1: Basic opportunity search
    print("\n" + "="*60)
    print("TEST: AdventHealth renewal opportunities")
    print("="*60)
    test_salesforce_opportunities("AdventHealth renewal", "AdventHealth")
    
    # Test 2: Check if other accounts leak in
    print("\n" + "="*60)
    print("TEST: JPMC opportunities (check for leaks)")
    print("="*60)
    test_salesforce_opportunities("JPMorgan Chase renewal", "JPMorgan Chase")
    
    # Test 3: Contacts search
    print("\n" + "="*60)
    print("TEST: AdventHealth contacts")
    print("="*60)
    test_salesforce_contacts("AdventHealth key contacts", "AdventHealth")
    
    # Test 4: Communications
    print("\n" + "="*60)
    print("TEST: AdventHealth recent calls")
    print("="*60)
    test_communications("AdventHealth call", "AdventHealth")
    
    # Test 5: Discover facets
    print("\n" + "="*60)
    print("TEST: Discover available Salesforce facets")
    print("="*60)
    discover_available_facets("salescloud")
    
    # Test 6: Strict filtering experiments
    print("\n" + "="*60)
    print("TEST: Strict filtering experiments")
    print("="*60)
    test_strict_opportunity_search("AdventHealth")
    
    # Test 7: JPMC quoted vs unquoted (uncomment to run)
    # test_quoted_jpmc()
    
    # Test 8: Post-filtering approach (uncomment to run)
    # test_with_post_filtering("JPMorgan Chase renewal", "JPMorgan Chase")
    
    # Test 9: Inspect full response for permission fields
    print("\n" + "="*60)
    print("TEST: Inspect full Glean response structure")
    print("="*60)
    inspect_full_response("AdventHealth renewal", "salescloud")
    
    # Test 10: Date filter keywords
    print("\n" + "="*60)
    print("TEST: Date Filter Keywords (past_day, past_week, etc.)")
    print("="*60)
    test_date_filter_keywords()
    
    # Test 11: Date range filter
    print("\n" + "="*60)
    print("TEST: Date Range Filter (last 30 days)")
    print("="*60)
    test_date_filter_range()
    
    # Test 12: NLP vs explicit filter comparison
    print("\n" + "="*60)
    print("TEST: NLP vs Explicit Date Filter Comparison")
    print("="*60)
    test_nlp_vs_filter_comparison("AdventHealth")
    
    # Test 13: Recent communications with time filter
    print("\n" + "="*60)
    print("TEST: Recent Communications (last 7 days)")
    print("="*60)
    test_communications_time_filtered("AdventHealth", days_back=7)


def test_gong_transcript_length(account: str = "AdventHealth"):
    """
    Test to verify we're getting full Gong transcripts, not truncated versions.
    
    This checks:
    1. What content fields are returned (llmContent vs snippets)
    2. The length of content returned
    3. Whether transcripts appear complete or cut off
    """
    print("\n" + "="*60)
    print("GONG TRANSCRIPT LENGTH TEST")
    print("="*60)
    
    # Search Gong specifically
    response = glean_search_raw(
        query=f"{account} call",
        datasources=["gong"],
        num_results=3,
        debug=True
    )
    
    results = response.get("results", [])
    print(f"\nFound {len(results)} Gong results\n")
    
    for i, r in enumerate(results, 1):
        doc = r.get("document", {})
        title = doc.get("title", "Untitled")
        url = doc.get("url", "")
        
        print(f"\n{'='*60}")
        print(f"RESULT {i}: {title}")
        print(f"URL: {url}")
        print(f"{'='*60}")
        
        # Check llmContent (preferred for LLM consumption)
        llm_content = r.get("llmContent")
        if llm_content:
            print(f"\n📄 llmContent (LLM-optimized content):")
            print(f"   Type: {type(llm_content)}")
            if isinstance(llm_content, str):
                print(f"   Length: {len(llm_content)} chars")
                print(f"   Preview: {llm_content[:500]}...")
                print(f"   Last 200 chars: ...{llm_content[-200:]}")
            elif isinstance(llm_content, list):
                total_len = sum(len(str(item)) for item in llm_content)
                print(f"   Items: {len(llm_content)}")
                print(f"   Total length: {total_len} chars")
                for j, item in enumerate(llm_content[:2]):
                    print(f"   Item {j}: {str(item)[:300]}...")
        else:
            print("\n⚠️  No llmContent returned")
        
        # Check snippets (fallback)
        snippets = r.get("snippets", [])
        if snippets:
            print(f"\n📋 Snippets:")
            print(f"   Count: {len(snippets)}")
            
            # Debug: show raw structure of first snippet
            print(f"\n   Raw first snippet structure:")
            print(f"   {json.dumps(snippets[0], indent=4, default=str)[:500]}")
            
            def get_snippet_text(s):
                if isinstance(s, dict):
                    # Try various paths Glean might use
                    text = s.get("text") or s.get("snippet", {}).get("text") or ""
                    if not text and "snippet" in s:
                        snippet_obj = s["snippet"]
                        if isinstance(snippet_obj, str):
                            text = snippet_obj
                        elif isinstance(snippet_obj, dict):
                            text = snippet_obj.get("text", "")
                    return text
                return str(s)
            
            # Show first 3 snippets
            total_snippet_len = 0
            for j, s in enumerate(snippets[:5]):
                text = get_snippet_text(s)
                total_snippet_len += len(text)
                if text:
                    print(f"   Snippet {j+1} length: {len(text)} chars")
                    print(f"   Preview: {text[:300]}...")
            
            # Calculate total for ALL snippets
            all_text = "".join(get_snippet_text(s) for s in snippets)
            print(f"\n   Total content length (all {len(snippets)} snippets): {len(all_text)} chars")
        else:
            print("\n⚠️  No snippets returned")
        
        # Check for any other content fields
        print(f"\n🔍 All top-level keys in result: {list(r.keys())}")
        print(f"🔍 All document keys: {list(doc.keys())}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("""
Key things to check:
1. Is llmContent present? (We set returnLlmContentOverSnippets=True)
2. What's the typical content length? 
   - Short (<1000 chars) = likely truncated
   - Medium (1000-5000 chars) = summary/highlights
   - Long (>5000 chars) = likely full transcript
3. Does content end mid-sentence? (indicates truncation)

Note: Glean's maxSnippetSize (currently 4000) limits snippet length.
For full transcripts, we may need to use Gong's API directly.
""")


def test_gong_full_content():
    """
    Test with maximum content settings to see if we can get more.
    """
    print("\n" + "="*60)
    print("GONG FULL CONTENT TEST (Max Settings)")
    print("="*60)
    
    if not GLEAN_API_TOKEN or not GLEAN_INSTANCE:
        print("ERROR: GLEAN_API_TOKEN or GLEAN_INSTANCE not set")
        return
    
    headers = {"Authorization": f"Bearer {GLEAN_API_TOKEN}"}
    
    # Try with maximum snippet size
    payload = {
        "query": "AdventHealth call",
        "pageSize": 1,
        "maxSnippetSize": 50000,  # Try max
        "requestOptions": {
            "datasourcesFilter": ["gong"],
            "returnLlmContentOverSnippets": True,
            "facetBucketSize": 100,
        }
    }
    
    print(f"Requesting with maxSnippetSize=50000...")
    
    with httpx.Client(timeout=30.0) as client:
        response = client.post(get_glean_api_url(), headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    
    results = data.get("results", [])
    if not results:
        print("No results found")
        return
    
    r = results[0]
    doc = r.get("document", {})
    
    print(f"\nTitle: {doc.get('title', 'Untitled')}")
    
    llm_content = r.get("llmContent")
    if llm_content:
        if isinstance(llm_content, str):
            print(f"llmContent length: {len(llm_content)} chars")
        elif isinstance(llm_content, list):
            total = sum(len(str(x)) for x in llm_content)
            print(f"llmContent total length: {total} chars")
    
    snippets = r.get("snippets", [])
    if snippets:
        total = sum(len(s.get("snippet", {}).get("text", "")) for s in snippets)
        print(f"Snippets total length: {total} chars")
    
    # Check if there's a way to get full content
    print("\nChecking for content/body fields in document...")
    for key in doc.keys():
        val = doc.get(key)
        if isinstance(val, str) and len(val) > 100:
            print(f"  {key}: {len(val)} chars")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "gong":
            test_gong_transcript_length(sys.argv[2] if len(sys.argv) > 2 else "AdventHealth")
        elif sys.argv[1] == "gong-full":
            test_gong_full_content()
        else:
            main()
    else:
        main()
