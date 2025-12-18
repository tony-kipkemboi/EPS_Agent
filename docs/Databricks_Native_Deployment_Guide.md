# EPS Agent - Databricks Native Deployment Guide

## Overview

This guide walks you through deploying the EPS Account Intelligence Agent using **Databricks-native components** once you have Unity Catalog permissions. This deployment method enables:

- **AI Playground** - Interactive testing without building a UI
- **MLflow Tracing** - Automatic observability for all agent operations
- **Unity Catalog** - Centralized model governance
- **Databricks Foundation Models** - No external API keys needed (optional)

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Unity Catalog Permissions**
  - `USE CATALOG` on your target catalog
  - `CREATE SCHEMA` permission (or access to an existing schema)
  - `CREATE MODEL` permission in the schema

- [ ] **Service Principal** (recommended) or **PATs enabled**
  - Required for `ChatDatabricks` to authenticate in Model Serving
  - Contact your Databricks admin if PATs are disabled

- [ ] **Foundation Model API Access**
  - Verify you can access endpoints like `databricks-meta-llama-3-1-70b-instruct`
  - Go to **Machine Learning → Serving** to check available models

- [ ] **Secrets Configured**
  - `eps-agent/GLEAN_API_TOKEN` - Your Glean API token
  - `eps-agent/GLEAN_INSTANCE` - Your Glean instance (e.g., `guild-be.glean.com`)

---

## Step 1: Request Unity Catalog Access

### 1.1 Identify Your Catalog

Check available catalogs in Databricks:

```sql
SHOW CATALOGS;
```

Common options:
- Use an existing catalog you have access to
- Request a new catalog from your admin

### 1.2 Request Permissions

Send this to your Databricks admin:

> **Subject:** Request Unity Catalog permissions for EPS Agent deployment
>
> Hi [Admin],
>
> I need the following permissions to deploy our EPS Account Intelligence Agent:
>
> 1. **USE CATALOG** on `[catalog_name]`
> 2. **CREATE SCHEMA** on `[catalog_name]` (or USE SCHEMA on existing schema)
> 3. **CREATE MODEL** permission in the target schema
>
> This is for deploying an AI agent that will be served via Model Serving.
>
> Thanks!

### 1.3 Verify Access

Once granted, verify:

```sql
-- Check catalog access
USE CATALOG your_catalog;

-- Create or use schema
CREATE SCHEMA IF NOT EXISTS your_catalog.eps_agent;

-- Verify
SHOW SCHEMAS IN your_catalog;
```

---

## Step 2: Configure Secrets

### 2.1 Create Secret Scope (if not exists)

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# Create scope
try:
    w.secrets.create_scope(name="eps-agent")
    print("✓ Secret scope created")
except Exception as e:
    print(f"Scope may already exist: {e}")
```

### 2.2 Add Secrets

```python
# Add Glean credentials
w.secrets.put_secret(
    scope="eps-agent",
    key="GLEAN_API_TOKEN",
    string_value="your-actual-glean-api-token"
)

w.secrets.put_secret(
    scope="eps-agent",
    key="GLEAN_INSTANCE",
    string_value="guild-be.glean.com"  # Your Glean instance
)

print("✓ Secrets configured")
```

### 2.3 Verify Secrets

```python
# List secrets (values are hidden)
secrets = list(w.secrets.list_secrets(scope="eps-agent"))
print("Secrets:", [s.key for s in secrets])
# Should show: ['GLEAN_API_TOKEN', 'GLEAN_INSTANCE']
```

---

## Step 3: Upload Agent Code

### 3.1 Create Workspace Directory

In Databricks:
1. Go to **Workspace** in the left sidebar
2. Navigate to your user folder: `/Workspace/Users/your.email@company.com/`
3. Create folder: `eps_agent`

### 3.2 Upload Files

Upload these files from your local `databricks/` folder:

| Local File | Databricks Path |
|------------|-----------------|
| `eps_agent_dbx_native.py` | `/Workspace/Users/your.email/eps_agent/eps_agent_dbx_native.py` |
| `deploy_native_notebook.py` | `/Workspace/Users/your.email/eps_agent/deploy_native_notebook.py` |

**Method 1: Drag & Drop**
- Open the folder in Databricks
- Drag files from your computer

**Method 2: Databricks CLI**
```bash
databricks workspace import \
  databricks/eps_agent_dbx_native.py \
  /Workspace/Users/your.email/eps_agent/eps_agent_dbx_native.py \
  --overwrite

databricks workspace import \
  databricks/deploy_native_notebook.py \
  /Workspace/Users/your.email/eps_agent/deploy_native_notebook.py \
  --overwrite
```

---

## Step 4: Update Configuration

### 4.1 Edit `eps_agent_dbx_native.py`

Open the file in Databricks and update lines 47-49:

```python
# Unity Catalog model path (update with your catalog/schema)
UC_CATALOG = "your_actual_catalog"    # ← Change this
UC_SCHEMA = "eps_agent"                # ← Change if needed
MODEL_NAME = f"{UC_CATALOG}.{UC_SCHEMA}.eps_account_agent"
```

### 4.2 Edit `deploy_native_notebook.py`

Update the configuration section (around line 40):

```python
# ============================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================

UC_CATALOG = "your_actual_catalog"      # ← Change this
UC_SCHEMA = "eps_agent"                  # ← Change if needed
MODEL_NAME = f"{UC_CATALOG}.{UC_SCHEMA}.eps_account_agent"

LLM_ENDPOINT = "databricks-gpt-5-1"     # Or your preferred model

AGENT_CODE_PATH = "/Workspace/Users/your.email@company.com/eps_agent"  # ← Update path

SECRET_SCOPE = "eps-agent"
EXPERIMENT_PATH = "/Shared/EPS_Agent_Production"
```

---

## Step 5: Run Deployment Notebook

### 5.1 Open the Notebook

1. Navigate to `/Workspace/Users/your.email/eps_agent/deploy_native_notebook.py`
2. Click to open
3. Attach to a cluster (ML Runtime recommended)

### 5.2 Run Step by Step

Run each cell in order:

| Step | Cell | What It Does |
|------|------|--------------|
| 1 | Install Dependencies | Installs langgraph, langchain, etc. |
| 2 | Configuration | Sets up your catalog/schema paths |
| 3 | Verify Prerequisites | Checks UC access and secrets |
| 4 | Import Agent | Loads the agent module |
| 5 | Test Locally | Quick test before deployment |
| 6 | Setup MLflow | Configures tracing and registry |
| 7 | Log Model | Saves model to Unity Catalog |
| 8 | Deploy Agent | Creates serving endpoint with `agents.deploy()` |
| 9 | Test Deployed | Verifies endpoint works |
| 10 | Done! | Shows next steps |

### 5.3 Expected Output

After Step 8, you should see:

```
✅ Agent deployed!
   Endpoint Name: eps_account_agent-endpoint
   Query URL: https://your-workspace.cloud.databricks.com/serving-endpoints/...
```

---

## Step 6: Test in AI Playground

### 6.1 Open AI Playground

1. Go to **Machine Learning** → **Playground** (left sidebar)
2. In the endpoint dropdown, select your agent endpoint
3. Start chatting!

### 6.2 Test Queries

Try these sample queries:

```
When is AdventHealth's renewal date?
```

```
What was the last call with Target?
```

```
Show me Wellstar's QBR deck
```

```
What's the sentiment from recent JPMC communications?
```

### 6.3 Verify Tool Calls

In AI Playground, you should see:
- The agent calling tools (search_salesforce, etc.)
- Sources being cited
- Links to original documents

---

## Step 7: Monitor with MLflow

### 7.1 View Traces

1. Go to **Machine Learning** → **Experiments**
2. Find `/Shared/EPS_Agent_Production`
3. Click on runs to see:
   - Input/output logs
   - Tool call traces
   - Latency metrics
   - Token usage

### 7.2 Enable Inference Tables (Optional)

For production monitoring:

```python
from databricks import agents

# Update endpoint with inference logging
agents.set_endpoint_config(
    endpoint_name="eps_account_agent-endpoint",
    inference_table_config={
        "catalog_name": "your_catalog",
        "schema_name": "eps_agent",
        "table_name_prefix": "eps_agent_logs"
    }
)
```

---

## Step 8: Connect Your UI

### 8.1 Get Endpoint URL

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

endpoint = w.serving_endpoints.get("eps_account_agent-endpoint")
print(f"URL: {endpoint.config.served_entities[0].entity_name}")
```

### 8.2 Query from UI

```python
import requests

ENDPOINT_URL = "https://your-workspace.cloud.databricks.com/serving-endpoints/eps_account_agent-endpoint/invocations"
TOKEN = "your-databricks-token"

response = requests.post(
    ENDPOINT_URL,
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={
        "messages": [{"role": "user", "content": "When is AdventHealth's renewal?"}],
        "thread_id": "user-123"
    }
)

print(response.json())
```

---

## Troubleshooting

### "PERMISSION_DENIED: User does not have USE CATALOG"

**Solution:** Request catalog access from your admin (see Step 1.2)

### "PERMISSION_DENIED: User does not have CREATE SCHEMA"

**Solution:** Either:
- Request CREATE SCHEMA permission
- Ask admin to create schema for you
- Use an existing schema you have access to

### "default auth: cannot configure default credentials"

**Problem:** `ChatDatabricks` can't authenticate in Model Serving

**Solution:** 
- Option A: Get Service Principal configured (ask admin)
- Option B: Use OpenAI instead (fall back to `eps_agent_dbx.py`)

### "Invalid secret provided"

**Problem:** Secrets not found or wrong scope name

**Solution:**
```python
# Verify scope exists
scopes = list(w.secrets.list_scopes())
print([s.name for s in scopes])

# Verify secrets exist
secrets = list(w.secrets.list_secrets("eps-agent"))
print([s.key for s in secrets])
```

### Agent returns generic response (not using tools)

**Problem:** LLM not invoking tools

**Solution:** Check that system prompt is being included. Run test locally first:
```python
agent = EPSAgentNative()
await agent._initialize_async()

# Test with verbose output
response = await agent.ainvoke(
    messages=[{"role": "user", "content": "When is AdventHealth's renewal?"}],
    thread_id="test",
    return_intermediate=True  # See tool calls
)
print(response)
```

---

## Migration from Current Deployment

If you're already running `eps_agent_dbx.py` (OpenAI version):

### Step 1: Keep Old Endpoint Running
Don't delete the existing endpoint until the new one is verified.

### Step 2: Deploy Native Version
Follow this guide to deploy alongside the old endpoint.

### Step 3: Test Native Endpoint
Verify AI Playground works and responses are correct.

### Step 4: Update UI to Use New Endpoint
Point your UI to the new endpoint URL.

### Step 5: Decommission Old Endpoint
Once verified, delete the old endpoint:
```python
w.serving_endpoints.delete("eps-account-agent")  # Old name
```

---

## Summary

| Phase | Action | Time Estimate |
|-------|--------|---------------|
| Prerequisites | Get UC permissions, configure secrets | 1-2 days (waiting) |
| Setup | Upload files, configure paths | 15 minutes |
| Deploy | Run notebook | 10-15 minutes |
| Test | AI Playground testing | 15 minutes |
| Monitor | Review MLflow traces | Ongoing |

**Total deployment time once permissions granted: ~45 minutes**

---

## Files Reference

| File | Purpose |
|------|---------|
| `eps_agent_dbx_native.py` | Agent code using ChatDatabricks |
| `deploy_native_notebook.py` | Databricks notebook for deployment |
| `eps_agent_dbx.py` | Current version (OpenAI fallback) |
| `deploy_notebook.py` | Current deployment notebook |

---

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review MLflow experiment logs
3. Check Model Serving endpoint logs
4. Verify secrets are correctly configured

---

*Last updated: December 2024*

