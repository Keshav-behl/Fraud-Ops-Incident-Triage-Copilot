"""Phase 6 acceptance test: a low-confidence (ambiguous) triage decision
triggers Slack escalation instead of silently auto-routing, and both Confirm
and Override correctly update the Jira ticket and the SQLite history table.

These tests hit the real Jira API and real Slack API. The escalation trigger
itself is forced via monkeypatching the classifier's output to a fixed
low-confidence TriageResult, so the test doesn't depend on the LLM's
confidence calibration for a "blended" ticket (which in practice sometimes
scores confidently anyway) — it deterministically exercises the actual
escalate -> Slack -> interaction -> DB/Jira update pipeline.
"""
import datetime
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.config import settings
from app.jira import client as jira_client
from app.main import app
from app.schemas import TriageResult
from app.storage import db

test_client = TestClient(app)

AMBIGUOUS_TITLE = "Disputed charge with a suspicious login beforehand"
AMBIGUOUS_DESCRIPTION = (
    "A customer disputes a $610 charge, but account logs also show a login from an "
    "unrecognized device and location shortly before the charge posted, raising the "
    "possibility this is account takeover rather than simple disputed-charge fraud."
)

LOW_CONFIDENCE_RESULT = TriageResult(
    risk_tier="Medium",
    confidence=40,
    suggested_team="Fraud Ops L2",
    suggested_sop="Manually review both disputed-charge and account-takeover precedents before routing.",
    rationale=(
        "This ticket blends signals from both disputed-charge-fraud precedents (KB-0013) and "
        "account-takeover precedents (KB-0025) — confidence is low because it is unclear which "
        "category applies."
    ),
)


def _sign(body: str, timestamp: str) -> str:
    basestring = f"v0:{timestamp}:{body}"
    return "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(), basestring.encode(), hashlib.sha256
    ).hexdigest()


def _post_interaction(payload: dict):
    body = urlencode({"payload": json.dumps(payload)})
    timestamp = str(int(time.time()))
    signature = _sign(body, timestamp)
    return test_client.post(
        "/slack/interactions",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature,
        },
    )


def _create_ticket(summary: str) -> str:
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = jira_client.create_issue(
        project_key=settings.JIRA_JSM_PROJECT_KEY,
        summary=f"[TEST] {summary} {stamp}",
        description=AMBIGUOUS_DESCRIPTION,
    )
    return result["key"]


def _escalate_ticket(monkeypatch, issue_key: str) -> dict:
    monkeypatch.setattr("app.agent.pipeline.classify", lambda title, desc: LOW_CONFIDENCE_RESULT)
    from app.agent.pipeline import handle_ticket

    return handle_ticket(issue_key, settings.JIRA_JSM_PROJECT_KEY, AMBIGUOUS_TITLE, AMBIGUOUS_DESCRIPTION)


def test_low_confidence_ticket_triggers_slack_escalation(monkeypatch):
    db.init_db()
    issue_key = _create_ticket("Escalation trigger test")

    outcome = _escalate_ticket(monkeypatch, issue_key)
    print(f"\nhandle_ticket() -> {outcome}")

    assert outcome["action"] == "escalated"
    assert outcome["ts"]

    pending = db.get_pending_by_ticket_key(issue_key)
    assert pending is not None
    assert pending["escalated"] == 1
    assert pending["decision"] == "pending"


def test_confirm_action_updates_ticket_and_history(monkeypatch):
    db.init_db()
    issue_key = _create_ticket("Confirm action test")
    outcome = _escalate_ticket(monkeypatch, issue_key)

    payload = {
        "type": "block_actions",
        "user": {"id": "U_TEST", "username": "test_reviewer"},
        "channel": {"id": outcome["channel"]},
        "message": {"ts": outcome["ts"]},
        "actions": [{"action_id": "confirm_triage", "value": issue_key}],
        "state": {"values": {}},
    }
    resp = _post_interaction(payload)
    print(f"\nconfirm interaction -> {resp.status_code} {resp.json()}")
    assert resp.status_code == 200

    history = db.get_history(issue_key)
    resolved = [r for r in history if r["decision"] == "confirmed"]
    assert len(resolved) == 1
    assert resolved[0]["final_risk_tier"] == LOW_CONFIDENCE_RESULT.risk_tier
    assert resolved[0]["final_team"] == LOW_CONFIDENCE_RESULT.suggested_team

    issue = jira_client.get_issue(issue_key)
    labels = issue["fields"]["labels"]
    assert any(l.startswith("risk-") for l in labels)
    assert any(l.startswith("team-") for l in labels)
    assert issue["fields"]["assignee"] is not None


def test_override_action_updates_ticket_and_history(monkeypatch):
    db.init_db()
    issue_key = _create_ticket("Override action test")
    outcome = _escalate_ticket(monkeypatch, issue_key)

    override_risk_tier = "Critical"
    override_team = "Trust & Safety"

    payload = {
        "type": "block_actions",
        "user": {"id": "U_TEST", "username": "test_reviewer"},
        "channel": {"id": outcome["channel"]},
        "message": {"ts": outcome["ts"]},
        "actions": [{"action_id": "override_triage", "value": issue_key}],
        "state": {
            "values": {
                "risk_tier_block": {
                    "risk_tier_select": {"selected_option": {"value": override_risk_tier}}
                },
                "team_block": {
                    "team_select": {"selected_option": {"value": override_team}}
                },
            }
        },
    }
    resp = _post_interaction(payload)
    print(f"\noverride interaction -> {resp.status_code} {resp.json()}")
    assert resp.status_code == 200

    history = db.get_history(issue_key)
    resolved = [r for r in history if r["decision"] == "overridden"]
    assert len(resolved) == 1
    assert resolved[0]["final_risk_tier"] == override_risk_tier
    assert resolved[0]["final_team"] == override_team

    issue = jira_client.get_issue(issue_key)
    labels = issue["fields"]["labels"]
    assert f"risk-{override_risk_tier.lower()}" in labels
    assert f"team-{override_team.lower().replace(' ', '-').replace('&', 'and')}" in labels

    # Critical risk tier should have also created a linked investigation sub-task.
    subtasks = issue["fields"].get("subtasks", [])
    assert len(subtasks) >= 1
