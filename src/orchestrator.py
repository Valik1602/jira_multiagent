import json
import re
import asyncio
from anthropic import Anthropic
from prompts import ORCHESTRATOR_PROMPT
from subagents import Subagent
from mcp_client import MCPClient

class Orchestrator:
    def __init__(self, api_key: str, mcp_client, use_http: bool = False):
        self.api_key = api_key
        self.mcp_client = mcp_client
        self.use_http = use_http
        self.client = Anthropic(api_key=api_key)
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
    
    def should_escalate_to_human(self, task: str, subagent_results: list) -> tuple:
        """
        Check if task requires human escalation based on 3 valid triggers:
        1. Explicit human request
        2. Policy gaps (not just violations)
        3. Inability to make progress after attempts

        Returns: (should_escalate: bool, reason: str, escalation_context: dict)
        """
        task_lower = task.lower()

        # Trigger 1: Explicit human request (absolute priority)
        human_keywords = [
            "human", "person", "real person", "actual person",
            "speak to someone", "talk to someone"
        ]
        for keyword in human_keywords:
            if keyword in task_lower:
                return True, "Customer explicitly requested human agent", {
                    "trigger": "explicit_request",
                    "original_request": task,
                    "priority": "immediate"
                }

        # Trigger 2: Policy gaps detection
        # Regex patterns allow filler words between tokens (e.g. "delete the SCRUM project")
        policy_gap_patterns = [
            (r'\bdelete\b.{0,40}\bproject\b', "delete project"),
            (r'\bmerge\b.{0,40}\bprojects?\b',  "merge projects"),
            (r'\bbulk\s+delete\b',               "bulk delete"),
            (r'\bchange\s+permissions?\b',        "change permissions"),
            (r'\badmin\s+access\b',               "admin access"),
            (r'\bconfigure\s+workflow\b',         "configure workflow"),
        ]
        for pattern, gap_type in policy_gap_patterns:
            if re.search(pattern, task_lower):
                print(f"   Policy gap matched: '{gap_type}' (pattern: {pattern!r})")
                return True, "Request involves policy gap - requires human judgment", {
                    "trigger": "policy_gap",
                    "gap_type": gap_type,
                    "recommendation": "Escalate for authorization decision"
                }

        # Trigger 3: Inability to make progress
        if not subagent_results:
            return False, "", {}

        error_count = 0
        transient_errors = 0
        for result in subagent_results:
            if isinstance(result, dict):
                if result.get("status") == "error":
                    error_count += 1
                    if result.get("failure_type") == "transient":
                        transient_errors += 1

        if error_count >= 2 and (error_count - transient_errors) > 0:
            return True, "Multiple subagents unable to make progress", {
                "trigger": "inability_to_progress",
                "failed_agents": error_count,
                "persistent_failures": error_count - transient_errors,
                "recommendation": "Human intervention needed to resolve system issues"
            }

        return False, "", {}

    def _create_escalation_response(
        self, reason: str, context: dict, task: str, subagent_results: list = None
    ) -> str:
        """Format escalation message for human handoff"""
        trigger_type = context.get("trigger", "unknown")

        response = f"""
🚨 ESCALATION REQUIRED

Trigger: {trigger_type.replace('_', ' ').title()}
Reason: {reason}

Original Request: {task}

Escalation Context:
"""
        for key, value in context.items():
            if key != "trigger":
                response += f"- {key.replace('_', ' ').title()}: {value}\n"

        if subagent_results:
            response += "\nWork Completed Before Escalation:\n"
            for i, result in enumerate(subagent_results, 1):
                if isinstance(result, dict):
                    agent_name = result.get("agent_type", f"Agent {i}")
                    status = result.get("status", "unknown")
                    response += f"- {agent_name}: {status}\n"

        response += "\n⚠️ This request requires human agent intervention."
        return response

    def _extract_structured_fields(self, text: str) -> dict:
        """Extract structured error fields from agent response text if JSON is present."""
        if not isinstance(text, str):
            return {}
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                parsed = json.loads(text[start:end])
                known_fields = [
                    "status", "failure_type", "should_retry",
                    "partial_results", "alternatives", "coverage_notes", "attempted_action"
                ]
                return {k: parsed[k] for k in known_fields if k in parsed}
        except (json.JSONDecodeError, ValueError):
            pass
        return {}

    def _handle_subagent_error(self, agent_name: str, response: dict) -> dict:
        """Handle subagent errors with intelligent recovery"""
        status = response.get("status", "success")

        if status == "success":
            return response

        failure_type = response.get("failure_type")
        should_retry = response.get("should_retry", False)

        # For transient failures, suggest retry
        if failure_type == "transient" and should_retry:
            alternatives = response.get("alternatives", [])
            print(f"⚠️  {agent_name} encountered transient error. Alternatives: {alternatives}")

        # Collect partial results if available
        partial = response.get("partial_results", [])
        if partial:
            print(f"✅ {agent_name} returned {len(partial)} partial results")

        return response

    async def execute(self, user_query: str):
        """Выполняет весь процесс"""
        # Step 1: escalation check BEFORE planning or running any subagents
        print(f"🔍 Checking escalation triggers...")
        should_escalate, escalation_reason, escalation_context = self.should_escalate_to_human(user_query, [])
        trigger = escalation_context.get("trigger")
        print(f"   Result → should_escalate={should_escalate}, trigger={trigger or 'none'}")

        if should_escalate and trigger in ("explicit_request", "policy_gap"):
            print(f"🚨 Escalating immediately ({trigger}) — skipping plan and subagents")
            return self._create_escalation_response(escalation_reason, escalation_context, user_query)

        # Step 2: plan and run subagents only when no immediate escalation is needed
        print("🧠 Orchestrator planning...")
        plan = self.plan(user_query)

        print(f"\n📋 Plan: {plan['reasoning']}")
        print(f"🤖 Creating {len(plan['subagents'])} subagents\n")

        MAX_RETRIES = 2
        all_coverage_notes = []

        for subagent_config in plan['subagents']:
            print(f"⚙️  Running {subagent_config['type']}...")

            result = None
            for attempt in range(MAX_RETRIES + 1):
                subagent = Subagent(
                    agent_type=subagent_config['type'],
                    task=subagent_config['task'],
                    api_key=self.api_key,
                    mcp_client=self.mcp_client
                )

                result = await subagent.execute()

                # Merge any structured error fields the agent included in its text response
                structured = self._extract_structured_fields(result.get("result", ""))
                result.update(structured)

                result = self._handle_subagent_error(subagent_config['type'], result)

                # Retry on transient failures
                if (result.get("failure_type") == "transient"
                        and result.get("should_retry", False)
                        and attempt < MAX_RETRIES):
                    print(f"🔄 Retrying {subagent_config['type']} (attempt {attempt + 2}/{MAX_RETRIES + 1})...")
                    await asyncio.sleep(2)
                    continue
                break

            all_coverage_notes.extend(result.get("coverage_notes", []))
            self.subagents_results.append(result)
            print(f"✅ {subagent_config['type']} completed\n")

        # Post-check: policy gaps or inability to progress after agents ran
        should_escalate, escalation_reason, escalation_context = self.should_escalate_to_human(
            user_query, self.subagents_results
        )
        if should_escalate:
            return self._create_escalation_response(
                escalation_reason, escalation_context, user_query, self.subagents_results
            )

        # Синтезируем финальный ответ
        final_report = self.synthesize(all_coverage_notes)

        # Проверяем цитаты
        citation_check = await self.verify_citations(final_report)

        return f"""{final_report}

---

## 📋 Citation Verification Report

{citation_check['result']}
"""
    
    def synthesize(self, coverage_notes: list = None):
        """Собирает результаты всех субагентов"""
        coverage_section = ""
        if coverage_notes:
            coverage_section = "\n\n⚠️ Coverage Notes:\n" + "\n".join(f"- {note}" for note in coverage_notes)

        synthesis_prompt = f"""Based on these subagent results, create a final report:

{json.dumps(self.subagents_results, indent=2)}

Synthesize the findings into a coherent summary with proper citations (Jira issue keys).{coverage_section}"""
        
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