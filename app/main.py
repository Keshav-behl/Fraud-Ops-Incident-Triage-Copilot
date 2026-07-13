import logging

from fastapi import BackgroundTasks, FastAPI, Request

from app.agent.pipeline import handle_ticket
from app.config import settings
from app.escalation.escalation_routes import router as escalation_router
from app.storage.db import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fraud_ops_triage")

app = FastAPI(title="Fraud/Ops Incident Triage Copilot")
app.include_router(escalation_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhooks/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    logger.info("Received Jira webhook: %s", payload)

    # Native Jira webhooks nest the issue under "issue"; Jira Automation's
    # "Issue data" web request body puts the issue fields at the top level.
    issue = payload.get("issue", payload)
    issue_key = issue.get("key")
    fields = issue.get("fields", {})
    issuetype = (fields.get("issuetype") or {}).get("name")
    logger.info("issue_key=%s issuetype=%s", issue_key, issuetype)

    if issuetype == "Sub-task":
        # Our own router creates these; avoid re-triaging them in a loop.
        logger.info("Skipping triage for sub-task %s", issue_key)
        return {"received": True, "issue_key": issue_key, "skipped": "sub-task"}

    title = fields.get("summary")
    description = fields.get("description")

    if issue_key and title:
        background_tasks.add_task(
            handle_ticket, issue_key, settings.JIRA_JSM_PROJECT_KEY, title, description or ""
        )

    return {"received": True, "issue_key": issue_key}
