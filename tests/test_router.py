"""Phase 5 acceptance test: a synthetic false-positive-fraud-block ticket
auto-labels, auto-assigns, and (if High/Critical) gets a sub-task, with zero
human steps.

These tests hit the real Jira API against the FT project.
"""
import datetime

from app.agent.triage_classifier import classify
from app.config import settings
from app.jira import client
from app.router.router import auto_route, should_auto_route
from app.schemas import TriageResult


def _create_test_ticket(summary_prefix: str, description: str) -> str:
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = client.create_issue(
        project_key=settings.JIRA_JSM_PROJECT_KEY,
        summary=f"[TEST] {summary_prefix} {stamp}",
        description=description,
    )
    return result["key"]


def test_false_positive_ticket_auto_labels_and_assigns():
    issue_key = _create_test_ticket(
        "Legitimate purchase blocked by fraud rule",
        "A customer's $340 purchase was auto-declined by the velocity rule after "
        "three back-to-back gift purchases during a holiday sale. All three "
        "transactions were made by the customer themselves.",
    )

    result = classify(
        "Legitimate purchase blocked by fraud rule",
        "A customer's $340 purchase was auto-declined by the velocity rule after "
        "three back-to-back gift purchases during a holiday sale. All three "
        "transactions were made by the customer themselves.",
    )
    print(f"\nclassify() -> risk_tier={result.risk_tier} confidence={result.confidence}")
    assert should_auto_route(result), "expected a clear-cut false-positive case to clear the confidence bar"

    routing = auto_route(issue_key, settings.JIRA_JSM_PROJECT_KEY, result)
    print(f"auto_route() -> {routing}")

    issue = client.get_issue(issue_key)
    fields = issue["fields"]
    assert set(routing["labels"]).issubset(set(fields["labels"]))
    assert fields["assignee"] is not None
    assert fields["assignee"]["accountId"] == routing["assignee_account_id"]

    if result.risk_tier in ("High", "Critical"):
        assert routing["subtask_key"] is not None
    else:
        assert routing["subtask_key"] is None


def test_high_risk_ticket_gets_linked_subtask():
    issue_key = _create_test_ticket(
        "Forced high-risk routing test",
        "Synthetic ticket used to verify the auto-subtask-creation code path "
        "for High/Critical risk tiers.",
    )

    forced_result = TriageResult(
        risk_tier="High",
        confidence=90,
        suggested_team="Fraud Ops L2",
        suggested_sop="Escalate to fraud ops for manual investigation.",
        rationale="Forced High risk_tier for Phase 5 sub-task creation test (KB-TEST).",
    )

    routing = auto_route(issue_key, settings.JIRA_JSM_PROJECT_KEY, forced_result)
    assert routing["subtask_key"] is not None

    subtask = client.get_issue(routing["subtask_key"])
    assert subtask["fields"]["parent"]["key"] == issue_key
