"""Create a real test ticket in the JSM project to confirm the webhook fires.

Run this while `uvicorn app.main:app --reload` is running and an ngrok tunnel
(or Jira Automation rule) is pointed at POST /webhooks/jira. Then check the
server logs for a line like:
    Received Jira webhook: {...}
"""
import datetime

from app.config import settings
from app.jira import client

if __name__ == "__main__":
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = f"[SMOKE TEST] Disputed charge ticket {stamp}"
    description = (
        "Synthetic smoke-test ticket created by scripts/smoke_test.py to verify "
        "the /webhooks/jira listener fires on issue creation. Safe to ignore/delete."
    )

    result = client.create_issue(
        project_key=settings.JIRA_JSM_PROJECT_KEY,
        summary=summary,
        description=description,
    )
    print(f"Created ticket {result['key']}: {settings.JIRA_SITE_URL}/browse/{result['key']}")
    print("Now check your local server logs for the webhook hit.")
