# Jira Multi-Agent System 🤖

Multi-agent system for Jira sprint analysis using Anthropic's Claude and MCP (Model Context Protocol).

## 🎯 Features

- **Multi-agent architecture** - Orchestrator coordinates specialized subagents
- **Sprint analysis** - Automated metrics and progress tracking
- **Blocker detection** - Identifies impediments across sprint issues
- **Citation verification** - Quality assurance for report accuracy
- **MCP integration** - Seamless Jira connectivity via Model Context Protocol

## 🏗️ Architecture

```
Orchestrator (Lead Agent)
  ├─→ Sprint Analyzer - Analyzes sprint metrics
  ├─→ Blocker Finder - Identifies blockers (uses MCP tools)
  ├─→ Report Generator - Creates formatted reports
  └─→ Citation Agent - Verifies claims with citations
       ↓
   MCP Client → Jira MCP Server → Jira Cloud API
```
## 📋 Prerequisites

- Python 3.12+
- Anthropic API key
- Jira Cloud instance with API access
- Jira MCP Server (separate repository)

## 🚀 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/YOUR_USERNAME/jira-multiagent.git
cd jira-multiagent
```

2. **Create virtual environment:**
```bash
uv venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux
```

3. **Install dependencies:**
```bash
uv pip install -e .
```

4. **Configure environment:**

Create `.env` file:
```
ANTHROPIC_API_KEY=your_anthropic_key_here
```

5. **Update MCP server path:**

Edit `src/main.py` line 19 with path to your Jira MCP server

## 💻 Usage

```bash
cd src
python main.py
```

The system will:
1. Connect to Jira MCP Server
2. Plan the analysis task
3. Execute subagents in sequence
4. Generate comprehensive sprint report
5. Verify citations for accuracy

## 📁 Project Structure

```
jira-multiagent/
├── src/
│   ├── main.py              # Entry point
│   ├── orchestrator.py      # Lead agent coordinator
│   ├── subagents.py         # Worker agents implementation
│   ├── prompts.py           # Agent system prompts
│   └── mcp_client.py        # MCP protocol client
├── .env                     # Environment variables (not in git)
├── .gitignore               # Git ignore rules
├── pyproject.toml           # Project dependencies
└── README.md                # This file
```

## 🔧 How It Works

### Agentic Loop
Each subagent operates in an autonomous loop:
1. **Think** - Analyze the task
2. **Act** - Call MCP tools (e.g., `get_issue`)
3. **Observe** - Process tool results
4. **Repeat** - Continue until task complete

### Multi-Agent Coordination
- **Orchestrator** plans task and creates subagents
- **Subagents** work independently with MCP tools
- **Synthesis** combines results into final report
- **Citation Agent** validates report accuracy

## 🛠️ Extending the System

Add new subagent types by updating `src/prompts.py`:

```python
YOUR_NEW_AGENT_PROMPT = """You are a [Role] Subagent.
Task: {task}
[Instructions]"""
```

Then add to `prompt_map` in `src/subagents.py`.

## 📚 Dependencies

- `anthropic` - Claude API client
- `python-dotenv` - Environment variable management
- `mcp` - Model Context Protocol

## 🔗 Related Projects

- [Jira MCP Server](link_to_jira_mcp_repo) - Required MCP server for Jira integration

## 📄 License

MIT

## 👤 Author

Valentyn Zelinskyi

## 🙏 Acknowledgments

Built following Anthropic's multi-agent architecture patterns from their Research feature.