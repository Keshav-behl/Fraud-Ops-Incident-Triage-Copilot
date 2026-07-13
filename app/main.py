import logging

from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fraud_ops_triage")

app = FastAPI(title="Fraud/Ops Incident Triage Copilot")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhooks/jira")
async def jira_webhook(request: Request):
    payload = await request.json()
    logger.info("Received Jira webhook: %s", payload)

    # Native Jira webhooks nest the issue under "issue"; Jira Automation's
    # "Issue data" web request body puts the issue fields at the top level.
    issue = payload.get("issue", payload)
    issue_key = issue.get("key")
    webhook_event = payload.get("webhookEvent")
    logger.info("webhookEvent=%s issue_key=%s", webhook_event, issue_key)

    return {"received": True, "issue_key": issue_key}
