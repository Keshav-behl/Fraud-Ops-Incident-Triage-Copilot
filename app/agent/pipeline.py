from app.agent.triage_classifier import classify
from app.escalation.slack_client import post_escalation
from app.rag.retriever import retrieve
from app.router.router import auto_route, should_auto_route
from app.storage import db


def handle_ticket(issue_key: str, project_key: str, ticket_title: str, ticket_description: str) -> dict:
    """Classify an incoming ticket and either auto-route it (high confidence)
    or escalate it to Slack for human confirmation (low confidence)."""
    result = classify(ticket_title, ticket_description)

    if should_auto_route(result):
        routing = auto_route(issue_key, project_key, result)
        db.insert_triage(
            ticket_key=issue_key,
            risk_tier=result.risk_tier,
            confidence=result.confidence,
            suggested_team=result.suggested_team,
            suggested_sop=result.suggested_sop,
            rationale=result.rationale,
            escalated=False,
            decision="auto",
        )
        return {"action": "auto_routed", **routing}

    precedents = retrieve(ticket_title, ticket_description)
    db.insert_triage(
        ticket_key=issue_key,
        risk_tier=result.risk_tier,
        confidence=result.confidence,
        suggested_team=result.suggested_team,
        suggested_sop=result.suggested_sop,
        rationale=result.rationale,
        escalated=True,
        decision="pending",
    )
    escalation = post_escalation(issue_key, ticket_title, ticket_description, result, precedents)
    return {"action": "escalated", **escalation}
