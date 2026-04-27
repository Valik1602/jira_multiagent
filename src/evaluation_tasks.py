"""
Evaluation tasks for Jira multi-agent system
Each task tests specific functionality
"""

EVALUATION_TASKS = [
    {
        "name": "move_single_issue_to_done",
        "prompt": "Change status of TEST-1 to Done",
        "expected_tools": ["jira_search_issues", "jira_update_status"],
        "max_tool_calls": 5,
        "expected_success": True
    },
    {
        "name": "move_multiple_issues_to_done",
        "prompt": "Move all In Progress issues assigned to Valentyn to Done",
        "expected_tools": ["jira_search_issues", "jira_update_status"],
        "max_tool_calls": 25,
        "expected_success": True
    },
    {
        "name": "find_blockers",
        "prompt": "Find all blocked or unassigned issues in TEST project",
        "expected_tools": ["jira_search_issues"],
        "max_tool_calls": 10,
        "expected_success": True
    },
    {
        "name": "add_to_sprint",
        "prompt": "Add TEST-145, TEST-146, TEST-147 to sprint 2",
        "expected_tools": ["jira_add_issues_to_sprint"],
        "max_tool_calls": 3,
        "expected_success": True
    },
    {
        "name": "analyze_sprint",
        "prompt": "Analyze current sprint health in TEST project",
        "expected_tools": ["jira_search_issues"],
        "max_tool_calls": 15,
        "expected_success": True
    },
    {
        "name": "create_issue",
        "prompt": "Create a new Bug in TEST project with summary 'Test evaluation bug'",
        "expected_tools": ["jira_create_issue"],
        "max_tool_calls": 3,
        "expected_success": True
    },
]