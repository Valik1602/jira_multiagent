import json
import asyncio
from anthropic import Anthropic
from prompts import ORCHESTRATOR_PROMPT
from subagents import Subagent
from mcp_client import MCPClient

class Orchestrator:
    def __init__(self, api_key: str, mcp_client: MCPClient):
        self.api_key = api_key
        self.client = Anthropic(api_key=api_key)
        self.mcp_client = mcp_client
        self.subagents_results = []
    
    def plan(self, user_query: str):
        """Планирует задачу и создаёт субагентов"""
        messages = [
            {
                "role": "user", 
                "content": f"{ORCHESTRATOR_PROMPT}\n\nUser query: {user_query}"
            }
        ]
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=messages
        )
        
        result_text = response.content[0].text
        
        try:
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            plan_json = json.loads(result_text[start:end])
            return plan_json
        except:
            print("Failed to parse plan, using fallback")
            return {
                "subagents": [
                    {"type": "sprint_analyzer", "task": user_query}
                ],
                "reasoning": "Fallback to single agent"
            }
    
    async def execute(self, user_query: str):
        """Выполняет весь процесс"""
        print("🧠 Orchestrator planning...")
        plan = self.plan(user_query)
        
        print(f"\n📋 Plan: {plan['reasoning']}")
        print(f"🤖 Creating {len(plan['subagents'])} subagents\n")
        
        # Создаём субагентов последовательно
        for subagent_config in plan['subagents']:
            print(f"⚙️  Running {subagent_config['type']}...")
            
            subagent = Subagent(
                agent_type=subagent_config['type'],
                task=subagent_config['task'],
                api_key=self.api_key,
                mcp_client=self.mcp_client
            )
            
            result = await subagent.execute()
            self.subagents_results.append(result)
            print(f"✅ {subagent_config['type']} completed\n")
        
        # Синтезируем финальный ответ
        final_report = self.synthesize()
        
        # Проверяем цитаты
        citation_check = await self.verify_citations(final_report)
        
        return f"""{final_report}

---

## 📋 Citation Verification Report

{citation_check['result']}
"""
    
    def synthesize(self):
        """Собирает результаты всех субагентов"""
        synthesis_prompt = f"""Based on these subagent results, create a final report:

{json.dumps(self.subagents_results, indent=2)}

Synthesize the findings into a coherent summary with proper citations (Jira issue keys)."""
        
        messages = [{"role": "user", "content": synthesis_prompt}]
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=messages
        )
        
        return response.content[0].text
    
    async def verify_citations(self, final_report: str):
        """Проверяет цитаты в финальном отчёте"""
        print("\n🔍 Running Citation Agent to verify claims...\n")
        
        # Создаём специального Citation Agent с данными в промпте
        messages = [
            {
                "role": "user",
                "content": f"""You are a Citation Verification Agent.

Here is the FINAL REPORT to verify:

---
{final_report}
---

Here is the RAW DATA from subagents (source of truth):

---
{json.dumps(self.subagents_results, indent=2)}
---

Your job:
1. Find every factual claim in the report
2. Check if it cites a Jira issue (TEST-XXX)
3. Verify citations match raw data
4. List: verified claims, missing citations, incorrect citations
5. Give confidence score 0-10

Output in plain text, not JSON."""
            }
        ]
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=messages
        )
        
        print("✅ Citation verification completed\n")
        
        return {"result": response.content[0].text}