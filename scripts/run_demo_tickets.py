"""Run a batch of synthetic tickets through the real end-to-end pipeline
(create real Jira ticket -> classify -> auto-route or escalate -> record to
triage_history), to populate real data for the Phase 7 dashboard.

Run: python -m scripts.run_demo_tickets
"""
import datetime
from datetime import timezone

from app.agent.pipeline import handle_ticket
from app.config import settings
from app.jira import client
from app.storage.db import init_db

TICKETS = [
    ("Customer says they never made this $89 purchase",
     "A customer emailed support insisting they never made a recent $89.20 charge "
     "showing up on their statement from an online electronics store."),
    ("Login from unfamiliar country followed by password change",
     "Security monitoring flagged a login from a country the customer has never "
     "logged in from before, followed minutes later by an unauthorized password change."),
    ("Merchant pushing back on a chargeback, says item was delivered",
     "A merchant submitted evidence disputing a chargeback, arguing tracking shows "
     "the package was delivered and signed for at the customer's address."),
    ("Customer angry their card was declined for no reason",
     "A customer called in upset that their card kept getting declined during "
     "checkout even though they had sufficient funds for a normal purchase."),
    ("Widespread checkout failures across multiple merchants",
     "Support received a flood of reports that checkout was failing with server "
     "errors across several unrelated merchants at the same time."),
    ("Hundreds of tiny declined authorizations from one IP block",
     "Fraud monitoring saw hundreds of sub-$2 authorization attempts against "
     "randomly generated card numbers, all from a narrow IP range within minutes."),
    ("Customer disputes a $1,200 charge at a furniture retailer",
     "A cardholder says they never authorized a $1,200 furniture purchase and "
     "wants it reversed; no prior disputes on file for this account."),
    ("Repeat customer complains about a second declined velocity block",
     "A customer who was previously cleared for a false-positive block last month "
     "is now being blocked again for a similar burst of purchases."),
    ("Card network reports a new BIN attack signature",
     "The card network's fraud intelligence unit flagged a new large-scale "
     "automated testing pattern hitting multiple merchants simultaneously."),
    ("Disputed charge that also shows a suspicious login beforehand",
     "A customer disputes a $610 charge, but account logs also show a login from "
     "an unrecognized device and location shortly before the charge posted, "
     "raising the possibility this is account takeover rather than simple fraud."),
]


def main():
    init_db()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for i, (title, description) in enumerate(TICKETS, start=1):
        ingested_at = datetime.datetime.now(timezone.utc).isoformat()
        issue = client.create_issue(
            project_key=settings.JIRA_JSM_PROJECT_KEY,
            summary=f"[DEMO] {title} ({stamp})",
            description=description,
        )
        issue_key = issue["key"]
        outcome = handle_ticket(
            issue_key, settings.JIRA_JSM_PROJECT_KEY, title, description, ingested_at
        )
        print(f"[{i}/{len(TICKETS)}] {issue_key}: {outcome['action']} — {title}")


if __name__ == "__main__":
    main()
