"""Unit tests for the 3 valid escalation triggers in Orchestrator."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from orchestrator import Orchestrator


def _make_orchestrator():
    """Instantiate Orchestrator without a live API key or MCP client."""
    orch = Orchestrator.__new__(Orchestrator)
    orch.api_key = "test"
    orch.mcp_client = None
    orch.use_http = False
    orch.subagents_results = []
    return orch


# ---------------------------------------------------------------------------
# Trigger 1 – Explicit human request
# ---------------------------------------------------------------------------

def test_explicit_human_keyword():
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human("I need to speak to a real person", [])
    assert should is True
    assert ctx["trigger"] == "explicit_request"
    assert ctx["priority"] == "immediate"
    print("✅ Trigger 1 – 'real person' keyword: PASS")


def test_explicit_human_variant():
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human("Can I talk to someone please?", [])
    assert should is True
    assert ctx["trigger"] == "explicit_request"
    print("✅ Trigger 1 – 'talk to someone' keyword: PASS")


def test_explicit_request_takes_priority_over_policy_gap():
    """Explicit request should be caught before policy-gap check."""
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human(
        "I need a human to help me delete project SCRUM", []
    )
    assert should is True
    assert ctx["trigger"] == "explicit_request"
    print("✅ Trigger 1 – explicit_request beats policy_gap: PASS")


# ---------------------------------------------------------------------------
# Trigger 2 – Policy gaps
# ---------------------------------------------------------------------------

def test_policy_gap_delete_project_adjacent():
    """'delete project SCRUM' — tokens adjacent, no filler words."""
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human("Can you delete project SCRUM?", [])
    assert should is True
    assert ctx["trigger"] == "policy_gap"
    assert ctx["gap_type"] == "delete project"
    print("✅ Trigger 2 – 'delete project SCRUM' (adjacent): PASS")


def test_policy_gap_delete_project_with_filler():
    """'Delete the SCRUM project' — words between 'delete' and 'project'."""
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human("Delete the SCRUM project", [])
    assert should is True
    assert ctx["trigger"] == "policy_gap"
    assert ctx["gap_type"] == "delete project"
    print("✅ Trigger 2 – 'Delete the SCRUM project' (filler words): PASS")


def test_policy_gap_admin_access():
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human("Give me admin access to this board", [])
    assert should is True
    assert ctx["trigger"] == "policy_gap"
    assert ctx["gap_type"] == "admin access"
    print("✅ Trigger 2 – 'admin access' policy gap: PASS")


def test_policy_gap_change_permissions():
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human("change permissions for the SCRUM board", [])
    assert should is True
    assert ctx["trigger"] == "policy_gap"
    assert ctx["gap_type"] == "change permissions"
    print("✅ Trigger 2 – 'change permissions' policy gap: PASS")


def test_policy_gap_bulk_delete():
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human("Perform a bulk delete of old issues", [])
    assert should is True
    assert ctx["trigger"] == "policy_gap"
    print("✅ Trigger 2 – 'bulk delete' policy gap: PASS")


# ---------------------------------------------------------------------------
# Trigger 3 – Inability to make progress
# ---------------------------------------------------------------------------

def test_inability_to_progress_two_persistent_failures():
    orch = _make_orchestrator()
    results = [
        {"status": "error", "failure_type": "validation", "agent_type": "sprint_analyzer"},
        {"status": "error", "failure_type": "business",   "agent_type": "blocker_finder"},
    ]
    should, reason, ctx = orch.should_escalate_to_human("Analyze sprint", results)
    assert should is True
    assert ctx["trigger"] == "inability_to_progress"
    assert ctx["failed_agents"] == 2
    assert ctx["persistent_failures"] == 2
    print("✅ Trigger 3 – two persistent failures: PASS")


def test_no_escalation_for_transient_only_errors():
    """All-transient failures should NOT escalate (retry may still succeed)."""
    orch = _make_orchestrator()
    results = [
        {"status": "error", "failure_type": "transient"},
        {"status": "error", "failure_type": "transient"},
    ]
    should, reason, ctx = orch.should_escalate_to_human("Analyze sprint", results)
    assert should is False
    print("✅ Trigger 3 – transient-only errors do NOT escalate: PASS")


def test_no_escalation_one_failure():
    """A single persistent failure is below the threshold."""
    orch = _make_orchestrator()
    results = [
        {"status": "error", "failure_type": "validation"},
        {"status": "success"},
    ]
    should, reason, ctx = orch.should_escalate_to_human("Analyze sprint", results)
    assert should is False
    print("✅ Trigger 3 – single failure does NOT escalate: PASS")


# ---------------------------------------------------------------------------
# No escalation for normal requests
# ---------------------------------------------------------------------------

def test_no_escalation_normal_request():
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human("Analyze current sprint progress", [])
    assert should is False
    assert ctx == {}
    print("✅ Normal request – no escalation: PASS")


def test_no_escalation_empty_results():
    orch = _make_orchestrator()
    should, reason, ctx = orch.should_escalate_to_human("Generate a sprint report", [])
    assert should is False
    print("✅ Normal request with empty results – no escalation: PASS")


# ---------------------------------------------------------------------------
# Escalation response formatter
# ---------------------------------------------------------------------------

def test_escalation_response_explicit_request():
    orch = _make_orchestrator()
    ctx = {
        "trigger": "explicit_request",
        "original_request": "speak to a real person",
        "priority": "immediate"
    }
    resp = orch._create_escalation_response("Explicit request", ctx, "speak to a real person")
    assert "ESCALATION REQUIRED" in resp
    assert "Explicit Request" in resp
    assert "human agent intervention" in resp
    print("✅ Response format – explicit_request: PASS")


def test_escalation_response_with_partial_work():
    orch = _make_orchestrator()
    ctx = {
        "trigger": "inability_to_progress",
        "failed_agents": 2,
        "persistent_failures": 2,
        "recommendation": "Human intervention needed"
    }
    partial = [
        {"agent_type": "sprint_analyzer", "status": "error"},
        {"agent_type": "blocker_finder",  "status": "error"},
    ]
    resp = orch._create_escalation_response("Cannot progress", ctx, "Analyze sprint", partial)
    assert "Work Completed Before Escalation" in resp
    assert "sprint_analyzer" in resp
    assert "blocker_finder" in resp
    print("✅ Response format – includes partial work log: PASS")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running escalation trigger tests...\n")

    test_explicit_human_keyword()
    test_explicit_human_variant()
    test_explicit_request_takes_priority_over_policy_gap()

    test_policy_gap_delete_project_adjacent()
    test_policy_gap_delete_project_with_filler()
    test_policy_gap_admin_access()
    test_policy_gap_change_permissions()
    test_policy_gap_bulk_delete()

    test_inability_to_progress_two_persistent_failures()
    test_no_escalation_for_transient_only_errors()
    test_no_escalation_one_failure()

    test_no_escalation_normal_request()
    test_no_escalation_empty_results()

    test_escalation_response_explicit_request()
    test_escalation_response_with_partial_work()

    print("\n✅ All escalation tests passed!")
