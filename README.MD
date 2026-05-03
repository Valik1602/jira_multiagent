# Jira Multi-Agent System

A multi-agent system for Jira sprint analysis using Claude AI and MCP (Model Context Protocol).

## What it does

The system accepts natural language tasks and executes them against Jira using a multi-agent architecture:

```
User Task → Orchestrator → MCP Client → Jira API
                ↓
         LLM Judge (evaluates output quality)
                ↓
         Human Review (optional manual scoring)
```

**Example tasks:**
```bash
python jira_agent.py "Change status of SCRUM-1 to Done"
python jira_agent.py "Show all open bugs in the current sprint"
python jira_agent.py "Assign SCRUM-5 to John and set priority to High"
```

## Architecture

| File | Purpose |
|------|---------|
| `jira_agent.py` | Entry point — accepts natural language task |
| `src/orchestrator.py` | Main coordinator agent |
| `src/mcp_client_http.py` | HTTP client for Jira MCP server |
| `llm_judge.py` | LLM-as-judge evaluation (Claude scores agent output) |
| `human_review.py` | Interactive human evaluation workflow |
| `evaluation.py` | Automated evaluation runner |
| `test_escalation.py` | Edge case and escalation tests |

## Key Features

- **Multi-agent orchestration** — coordinator delegates tasks to specialized agents
- **LLM-as-Judge evaluation** — Claude evaluates agent output on 4 criteria: accuracy, completeness, tool efficiency, source quality
- **Human review workflow** — side-by-side comparison of LLM judge scores vs human scores
- **Evaluation persistence** — results saved as JSON with timestamps for comparison across runs

## Setup

### 1. Install dependencies
```bash
pip install anthropic python-dotenv httpx
```

### 2. Configure environment
```bash
cp .env.example .env
```

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=your-jira-token
```

### 3. Start Jira MCP server
```bash
# In a separate terminal — requires jira-mcp repo
cd ../jira-mcp
python mcp_server_http.py
```

### 4. Run the agent
```bash
python jira_agent.py "your task here"
```

## Evaluation

### Run automated evaluation
```bash
python evaluation.py
```

### Review results with LLM Judge + Human scoring
```bash
python human_review.py evaluation_results_<timestamp>.json
```

The human review workflow shows you the LLM Judge's scores and lets you compare them with your own ratings.

## Related

- [jira-mcp](https://github.com/Valik1602/jira-mcp) — Custom Jira MCP server with 8 tools (SSE/HTTP/stdio transports)
- [code-review-agent](https://github.com/Valik1602/code-review-agent) — AI Code Review Agent that creates Jira tickets
