import json
import asyncio
from anthropic import Anthropic
from prompts import SPRINT_ANALYZER_PROMPT, BLOCKER_FINDER_PROMPT, REPORT_GENERATOR_PROMPT, CITATION_AGENT_PROMPT, STATUS_CHANGER_PROMPT


class SubagentResponse:
    """Structured response format for subagent execution with error propagation support"""
    def __init__(
        self,
        status: str = "success",  # success | partial_failure | error
        results: list = None,
        failure_type: str = None,  # transient | validation | business | permission
        attempted_action: dict = None,
        partial_results: list = None,
        alternatives: list = None,
        coverage_notes: list = None,
        should_retry: bool = False
    ):
        self.status = status
        self.results = results or []
        self.failure_type = failure_type
        self.attempted_action = attempted_action or {}
        self.partial_results = partial_results or []
        self.alternatives = alternatives or []
        self.coverage_notes = coverage_notes or []
        self.should_retry = should_retry

    def to_dict(self):
        return {
            "status": self.status,
            "results": self.results,
            "failure_type": self.failure_type,
            "attempted_action": self.attempted_action,
            "partial_results": self.partial_results,
            "alternatives": self.alternatives,
            "coverage_notes": self.coverage_notes,
            "should_retry": self.should_retry
        }


AGENT_TOOL_MAPPING = {
    "status_changer": [
        "jira_search_issues",
        "jira_update_status"
    ],
    "issue_creator": [
        "jira_search_issues",
        "jira_create_issue"
    ],
    "sprint_analyzer": [
        "jira_search_issues",
        "jira_analyze_issues_with_ai"
    ],
    "blocker_finder": [
        "jira_search_issues"
    ],
    "report_generator": [
        "jira_search_issues"
    ],
    "citation_agent": [
        "jira_search_issues"
    ]
}

class Subagent:
    def __init__(self, agent_type: str, task: str, api_key: str, mcp_client):
        self.agent_type = agent_type
        self.task = task
        self.client = Anthropic(api_key=api_key)
        self.mcp_client = mcp_client
        
        self.prompt_map = {
            "sprint_analyzer": SPRINT_ANALYZER_PROMPT,
            "blocker_finder": BLOCKER_FINDER_PROMPT,
            "report_generator": REPORT_GENERATOR_PROMPT,
            "citation_agent": CITATION_AGENT_PROMPT,
            "status_changer": STATUS_CHANGER_PROMPT,
        }
    
    async def execute(self):
        """Выполняет задачу субагента с доступом к MCP инструментам"""
        prompt = self.prompt_map[self.agent_type].format(task=self.task)
        
        # Получаем список инструментов из MCP сервера
        mcp_tools = await self.mcp_client.list_tools()
        
        # Конвертируем MCP tools в формат Anthropic API
        # Поддержка и STDIO и HTTP clients
        tools = []
        for tool in mcp_tools:
            if hasattr(tool, 'name'):
                # STDIO client (mcp_client.py)
                tools.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema
                })
            else:
                # HTTP client (mcp_client_http.py)
                tools.append({
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("input_schema", {"type": "object", "properties": {}})
                })

        allowed_tool_names = AGENT_TOOL_MAPPING.get(self.agent_type)
        if allowed_tool_names is not None:
            tools = [t for t in tools if t["name"] in allowed_tool_names]

        messages = [{"role": "user", "content": prompt}]
        
        # Лимит на количество tool calls
        max_iterations = 15
        iteration = 0
        
        # Агентный цикл: Claude вызывает инструменты пока не завершит задачу
        while True:
            iteration += 1
            
            # Проверка лимита
            if iteration > max_iterations:
                print(f"   ⚠️  Reached max iterations ({max_iterations}), stopping agent")
                result_text = next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    f"Agent stopped after {max_iterations} tool calls. Partial results may be available."
                )
                return {
                    "agent_type": self.agent_type,
                    "task": self.task,
                    "result": result_text
                }
            
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=messages,
                tools=tools
            )
            
            # Если Claude завершил работу
            if response.stop_reason == "end_turn":
                result_text = next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "No text result"
                )
                return {
                    "agent_type": self.agent_type,
                    "task": self.task,
                    "result": result_text
                }
            
            # Если Claude хочет вызвать инструменты
            if response.stop_reason == "tool_use":
                # Добавляем ответ Claude в историю
                messages.append({"role": "assistant", "content": response.content})
                
                # Выполняем все tool_use блоки
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"   🔧 Calling tool: {block.name}")
                        
                        # Вызываем инструмент через MCP клиент
                        # Работает и для STDIO и для HTTP client
                        result = await self.mcp_client.call_tool(block.name, block.input)
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result)
                        })
                
                # Добавляем результаты инструментов
                messages.append({"role": "user", "content": tool_results})
            else:
                # Неожиданная остановка
                return {
                    "agent_type": self.agent_type,
                    "task": self.task,
                    "result": f"Unexpected stop: {response.stop_reason}"
                }