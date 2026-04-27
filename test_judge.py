from llm_judge import LLMJudge

judge = LLMJudge()

# Тестовый вывод агента
test_output = """
# Status Change Report

Successfully changed status of TEST-1 from In Progress to Done.

## Details:
- Issue: TEST-1
- Previous Status: In Progress  
- New Status: Done
- Updated: 2026-04-27

The operation completed successfully.
"""

result = judge.evaluate_output(
    task_name="move_single_issue_to_done",
    task_prompt="Change status of TEST-1 to Done",
    agent_output=test_output,
    expected_criteria="Expected tools: jira_search_issues, jira_update_status. Max tool calls: 5"
)

print("🤖 LLM Judge Result:")
print(f"Overall Score: {result.get('overall_score')}/1.0")
print(f"Pass: {result.get('pass')}")
print(f"Accuracy: {result.get('accuracy')}")
print(f"Completeness: {result.get('completeness')}")
print(f"Tool Efficiency: {result.get('tool_efficiency')}")
print(f"Source Quality: {result.get('source_quality')}")
print(f"\nFeedback: {result.get('feedback')}")