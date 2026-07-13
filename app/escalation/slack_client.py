from slack_sdk import WebClient

from app.config import settings
from app.schemas import RetrievedRecord, TriageResult

_client = WebClient(token=settings.SLACK_BOT_TOKEN)

RISK_TIER_OPTIONS = ["Low", "Medium", "High", "Critical"]
TEAM_OPTIONS = [
    "Fraud Ops L1",
    "Fraud Ops L2",
    "Trust & Safety",
    "Merchant Risk",
    "Chargeback Ops",
    "Card Risk Team",
    "Payments Engineering",
    "Platform Reliability",
]


def _option(label: str) -> dict:
    return {"text": {"type": "plain_text", "text": label}, "value": label}


def _build_blocks(
    issue_key: str,
    ticket_title: str,
    ticket_description: str,
    triage_result: TriageResult,
    precedents: list[RetrievedRecord],
) -> list[dict]:
    precedent_lines = "\n".join(
        f"• *{p.record.id}* ({p.record.category}, sim={p.similarity:.2f}): {p.record.title}"
        for p in precedents
    )

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f":warning: Triage needs review — {issue_key}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{ticket_title}*\n{ticket_description}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Model's tentative decision* (confidence {triage_result.confidence:.0f}% — "
                    f"below threshold, needs human confirmation)\n"
                    f"*Risk tier:* {triage_result.risk_tier}\n"
                    f"*Suggested team:* {triage_result.suggested_team}\n"
                    f"*Suggested SOP:* {triage_result.suggested_sop}\n"
                    f"*Rationale:* {triage_result.rationale}"
                ),
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Retrieved precedents:*\n{precedent_lines}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "block_id": "risk_tier_block",
            "text": {"type": "mrkdwn", "text": "Override risk tier:"},
            "accessory": {
                "type": "static_select",
                "action_id": "risk_tier_select",
                "placeholder": {"type": "plain_text", "text": "Risk tier"},
                "options": [_option(o) for o in RISK_TIER_OPTIONS],
            },
        },
        {
            "type": "section",
            "block_id": "team_block",
            "text": {"type": "mrkdwn", "text": "Override team:"},
            "accessory": {
                "type": "static_select",
                "action_id": "team_select",
                "placeholder": {"type": "plain_text", "text": "Team"},
                "options": [_option(o) for o in TEAM_OPTIONS],
            },
        },
        {
            "type": "actions",
            "block_id": "decision_actions",
            "elements": [
                {
                    "type": "button",
                    "style": "primary",
                    "text": {"type": "plain_text", "text": "Confirm model's decision"},
                    "action_id": "confirm_triage",
                    "value": issue_key,
                },
                {
                    "type": "button",
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Override with selections above"},
                    "action_id": "override_triage",
                    "value": issue_key,
                },
            ],
        },
    ]


def post_escalation(
    issue_key: str,
    ticket_title: str,
    ticket_description: str,
    triage_result: TriageResult,
    precedents: list[RetrievedRecord],
) -> dict:
    blocks = _build_blocks(issue_key, ticket_title, ticket_description, triage_result, precedents)
    response = _client.chat_postMessage(
        channel=settings.SLACK_ESCALATION_CHANNEL,
        text=f"Triage needs review — {issue_key}",
        blocks=blocks,
    )
    return {"channel": response["channel"], "ts": response["ts"]}


def update_message(channel: str, ts: str, text: str) -> None:
    _client.chat_update(channel=channel, ts=ts, text=text, blocks=[
        {"type": "section", "text": {"type": "mrkdwn", "text": text}}
    ])
