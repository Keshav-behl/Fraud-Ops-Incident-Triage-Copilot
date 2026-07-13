import hashlib
import hmac
import json
import time

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.escalation import slack_client
from app.router.router import auto_route
from app.schemas import TriageResult
from app.storage import db

router = APIRouter()


def _verify_slack_signature(timestamp: str, body: bytes, signature: str) -> bool:
    if not timestamp or not signature:
        return False
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    basestring = f"v0:{timestamp}:{body.decode()}"
    computed = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(), basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


@router.post("/slack/interactions")
async def slack_interactions(request: Request):
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not _verify_slack_signature(timestamp, body, signature):
        raise HTTPException(status_code=401, detail="invalid Slack signature")

    form = await request.form()
    payload = json.loads(form["payload"])

    action = payload["actions"][0]
    action_id = action["action_id"]
    issue_key = action["value"]
    user = payload["user"].get("username") or payload["user"]["id"]
    channel = payload["channel"]["id"]
    ts = payload["message"]["ts"]

    pending = db.get_pending_by_ticket_key(issue_key)
    if pending is None:
        return {"text": f"No pending triage found for {issue_key} (already resolved?)."}

    if action_id == "confirm_triage":
        final_risk_tier = pending["risk_tier"]
        final_team = pending["suggested_team"]
        triage_result = TriageResult(
            risk_tier=final_risk_tier,
            confidence=100,
            suggested_team=final_team,
            suggested_sop=pending["suggested_sop"],
            rationale=pending["rationale"],
        )
        auto_route(issue_key, settings.JIRA_JSM_PROJECT_KEY, triage_result)
        db.resolve_decision(issue_key, "confirmed", final_risk_tier, final_team)
        slack_client.update_message(
            channel, ts,
            f":white_check_mark: {issue_key} confirmed by <@{user}> as "
            f"{final_risk_tier}/{final_team} and routed.",
        )
        return {"text": "confirmed"}

    if action_id == "override_triage":
        state_values = payload.get("state", {}).get("values", {})
        selected_risk_tier = (
            state_values.get("risk_tier_block", {})
            .get("risk_tier_select", {})
            .get("selected_option", {})
            or {}
        ).get("value")
        selected_team = (
            state_values.get("team_block", {})
            .get("team_select", {})
            .get("selected_option", {})
            or {}
        ).get("value")

        if not selected_risk_tier or not selected_team:
            return {"text": "Select both a risk tier and a team before overriding."}

        triage_result = TriageResult(
            risk_tier=selected_risk_tier,
            confidence=100,
            suggested_team=selected_team,
            suggested_sop=pending["suggested_sop"],
            rationale=f"Human override by {user}. Original model rationale: {pending['rationale']}",
        )
        auto_route(issue_key, settings.JIRA_JSM_PROJECT_KEY, triage_result)
        db.resolve_decision(issue_key, "overridden", selected_risk_tier, selected_team)
        slack_client.update_message(
            channel, ts,
            f":twisted_rightwards_arrows: {issue_key} overridden by <@{user}> to "
            f"{selected_risk_tier}/{selected_team} and routed.",
        )
        return {"text": "overridden"}

    return {"text": "unhandled action"}
