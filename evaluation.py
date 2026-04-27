import asyncio
import time
import json
from datetime import datetime
import os
import sys
from dotenv import load_dotenv
from llm_judge import LLMJudge

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from orchestrator import Orchestrator
from mcp_client import MCPClient
from evaluation_tasks import EVALUATION_TASKS

load_dotenv()

class EvaluationRunner:
    def __init__(self):
        self.results = []
        self.mcp_client = None
        self.orchestrator = None
        self.llm_judge = LLMJudge()
        
    async def setup(self):
        """Подключаемся к MCP один раз для всех тестов"""
        print("\n🔌 Connecting to MCP Server...")
        self.mcp_client = MCPClient(
            command="uv",
            args=["--directory", r"C:\Users\ValentynZelinskyi\Desktop\jira-mcp", "run", "mcp", "run", "mcp_server.py"]
        )
        await self.mcp_client.connect()
        
        self.orchestrator = Orchestrator(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            mcp_client=self.mcp_client
        )
        print("✅ Connected to MCP Server\n")
        
    async def run_single_task(self, task):
        """Запускает один evaluation task"""
        print(f"\n{'='*60}")
        print(f"🧪 Running: {task['name']}")
        print(f"📝 Prompt: {task['prompt']}")
        print(f"{'='*60}")
        
        # Засекаем время
        start_time = time.time()
        
        try:
            # Выполняем задачу
            result = await self.orchestrator.execute(task['prompt'])
            
            # Считаем tool calls из subagents_results
            total_tool_calls = 0
            for agent_result in self.orchestrator.subagents_results:
                total_tool_calls += len(str(agent_result).split('🔧 Calling tool:')) - 1
            
            elapsed_time = time.time() - start_time
            
            # Проверяем успешность
            success = result is not None and len(result) > 0
            
            # LLM Judge оценивает качество
            judge_result = None
            if success:
                print(f"\n🤖 Evaluating output quality with LLM Judge...")
                judge_result = self.llm_judge.evaluate_output(
                    task_name=task['name'],
                    task_prompt=task['prompt'],
                    agent_output=result[:5000],  # Первые 5000 символов
                    expected_criteria=f"Expected tools: {task['expected_tools']}, Max tool calls: {task['max_tool_calls']}"
                )
                print(f"   Judge score: {judge_result.get('overall_score', 0):.2f}/1.0")
                print(f"   Pass: {'✅' if judge_result.get('pass') else '❌'}")
            
            # Сохраняем результат
            test_result = {
                "name": task['name'],
                "prompt": task['prompt'],
                "success": success,
                "tool_calls": total_tool_calls,
                "time_seconds": round(elapsed_time, 2),
                "passed": (
                    success and 
                    total_tool_calls <= task['max_tool_calls'] and
                    (judge_result.get('pass', False) if judge_result else True)
                ),
                "expected_max_calls": task['max_tool_calls'],
                "llm_judge": judge_result
            }
            
            self.results.append(test_result)
            
            # Выводим результат
            status = "✅ PASS" if test_result['passed'] else "❌ FAIL"
            print(f"\n{status}")
            print(f"  Tool calls: {total_tool_calls}/{task['max_tool_calls']}")
            print(f"  Time: {elapsed_time:.2f}s")
            if judge_result:
                print(f"  LLM Judge: {judge_result.get('overall_score', 0):.2f}/1.0")
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            self.results.append({
                "name": task['name'],
                "success": False,
                "error": str(e),
                "passed": False
            })
    
    async def run_all_tasks(self):
        """Запускает все evaluation tasks"""
        print("\n" + "="*60)
        print("🚀 Starting Evaluation")
        print(f"📊 Total tasks: {len(EVALUATION_TASKS)}")
        print("="*60)
        
        # Подключаемся один раз
        await self.setup()
        
        # Запускаем все тесты
        for i, task in enumerate(EVALUATION_TASKS, 1):
            print(f"\n📌 Test {i}/{len(EVALUATION_TASKS)}")
            await self.run_single_task(task)
        
        self.print_summary()
        self.save_results()
    
    def print_summary(self):
        """Выводит итоговую статистику"""
        print("\n" + "="*60)
        print("📊 EVALUATION SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get('passed', False))
        failed = total - passed
        
        # Средний LLM Judge score
        judge_scores = [r.get('llm_judge', {}).get('overall_score', 0) 
                       for r in self.results if r.get('llm_judge')]
        avg_judge_score = sum(judge_scores) / len(judge_scores) if judge_scores else 0
        
        print(f"\n✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        print(f"❌ Failed: {failed}/{total} ({failed/total*100:.1f}%)")
        print(f"📊 Average LLM Judge Score: {avg_judge_score:.2f}/1.0")
        
        print("\n📋 Detailed Results:")
        for result in self.results:
            status = "✅" if result.get('passed') else "❌"
            name = result['name']
            if 'tool_calls' in result:
                calls = result['tool_calls']
                max_calls = result.get('expected_max_calls', 'N/A')
                time_s = result.get('time_seconds', 0)
                judge_score = result.get('llm_judge', {}).get('overall_score', 0)
                print(f"  {status} {name}: {calls}/{max_calls} calls, {time_s}s, judge: {judge_score:.2f}")
            else:
                print(f"  {status} {name}: ERROR - {result.get('error', 'Unknown')}")
    
    def save_results(self):
        """Сохраняет результаты в JSON"""
        filename = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total': len(self.results),
                'passed': sum(1 for r in self.results if r.get('passed', False)),
                'results': self.results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")

async def main():
    runner = EvaluationRunner()
    await runner.run_all_tasks()

if __name__ == "__main__":
    asyncio.run(main())