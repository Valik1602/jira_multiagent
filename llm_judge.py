"""
LLM-as-judge evaluation system
Uses Claude to evaluate agent outputs against quality criteria
"""

import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

class LLMJudge:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
    def evaluate_output(self, task_name, task_prompt, agent_output, expected_criteria):
        """
        Оценивает output агента по критериям
        
        Returns:
        {
            "overall_score": 0.0-1.0,
            "pass": True/False,
            "scores": {
                "accuracy": 0.0-1.0,
                "completeness": 0.0-1.0,
                "tool_efficiency": 0.0-1.0,
                "source_quality": 0.0-1.0
            },
            "feedback": "Detailed feedback..."
        }
        """
        
        judge_prompt = f"""You are evaluating the quality of an AI agent's output.

TASK: {task_name}
USER QUERY: {task_prompt}

AGENT OUTPUT:
{agent_output}

EVALUATION CRITERIA:
{expected_criteria}

Please evaluate the agent's output on a scale of 0.0 to 1.0 for each criterion:

1. **Factual Accuracy** (0.0-1.0): Are all claims accurate and verifiable?
2. **Completeness** (0.0-1.0): Did the agent address all aspects of the query?
3. **Tool Efficiency** (0.0-1.0): Did the agent use appropriate tools without unnecessary calls?
4. **Source Quality** (0.0-1.0): For research tasks, did it use high-quality, authoritative sources?

Output your evaluation in this exact JSON format:
{{
  "accuracy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "tool_efficiency": 0.0-1.0,
  "source_quality": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "pass": true/false,
  "feedback": "Brief explanation of strengths and weaknesses"
}}

Be objective and constructive. A pass requires overall_score >= 0.7."""

        response = self.client.messages.create(
         model="claude-sonnet-4-6",  # Используем стабильную версию
         max_tokens=2000,
            messages=[{"role": "user", "content": judge_prompt}]
        )
        
        # Parse JSON response
        import json
        try:
            result_text = response.content[0].text
            # Remove markdown code fences if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text.strip())
            return result
        except Exception as e:
            print(f"⚠️  Failed to parse judge output: {e}")
            return {
                "overall_score": 0.0,
                "pass": False,
                "feedback": f"Error parsing judge output: {str(e)}"
            }