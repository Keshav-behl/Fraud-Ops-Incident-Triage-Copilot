from app.config import settings
from app.jira import client
from app.schemas import TriageResult

RISK_LABEL_PREFIX = "risk"
TEAM_LABEL_PREFIX = "team"
AUTO_SUBTASK_TIERS = ("High", "Critical")
JIRA_SUMMARY_MAX_LEN = 255


def _slugify(text: str) -> str:
    return text.strip().lower().replace(" ", "-").replace("&", "and")


def _truncate_for_summary(prefix: str, text: str) -> str:
    """Jira issue summaries are capped at 255 chars; truncate the variable
    part and keep the full text in the description instead."""
    budget = JIRA_SUMMARY_MAX_LEN - len(prefix)
    if len(text) <= budget:
        return f"{prefix}{text}"
    return f"{prefix}{text[:budget - 3]}..."


def should_auto_route(triage_result: TriageResult) -> bool:
    """High-confidence decisions auto-route; below-threshold ones must be
    escalated to a human instead (Phase 6)."""
    return triage_result.confidence >= settings.CONFIDENCE_ESCALATION_THRESHOLD


def auto_route(issue_key: str, project_key: str, triage_result: TriageResult) -> dict:
    """Deterministically label, assign, and (for High/Critical risk) create a
    linked investigation sub-task for a high-confidence triage decision.

    Assignment targets the Jira account running this copilot (the only real
    account available on a personal/dev Jira site) — in a multi-agent team
    this would resolve `suggested_team` to that team's queue/account instead.
    """
    risk_label = f"{RISK_LABEL_PREFIX}-{_slugify(triage_result.risk_tier)}"
    team_label = f"{TEAM_LABEL_PREFIX}-{_slugify(triage_result.suggested_team)}"
    labels = [risk_label, team_label]

    client.update_labels(issue_key, labels)

    account_id = client.get_current_user_account_id()
    client.assign_issue(issue_key, account_id)

    comment = (
        f"Auto-triaged (confidence={triage_result.confidence:.0f}%): "
        f"risk_tier={triage_result.risk_tier}, suggested_team={triage_result.suggested_team}\n\n"
        f"Suggested SOP: {triage_result.suggested_sop}\n\n"
        f"Rationale: {triage_result.rationale}"
    )
    client.add_comment(issue_key, comment)

    subtask_key = None
    if triage_result.risk_tier in AUTO_SUBTASK_TIERS:
        summary = _truncate_for_summary("[Auto] Investigate: ", triage_result.suggested_sop)
        description = f"Suggested SOP: {triage_result.suggested_sop}\n\nRationale: {triage_result.rationale}"
        subtask = client.create_subtask(
            parent_key=issue_key,
            project_key=project_key,
            summary=summary,
            description=description,
        )
        subtask_key = subtask["key"]

    return {
        "issue_key": issue_key,
        "labels": labels,
        "assignee_account_id": account_id,
        "subtask_key": subtask_key,
    }
