"""Phase 4 acceptance test: 10 tickets each produce valid structured TriageResult
output, with rationale referencing at least one retrieved precedent (spot-check
manually via the printed output).
"""
from app.agent.triage_classifier import classify

TEST_TICKETS = [
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


def test_ten_tickets_produce_valid_triage():
    for i, (title, description) in enumerate(TEST_TICKETS, start=1):
        result = classify(title, description)
        print(f"\n[{i}] {title}")
        print(f"    risk_tier={result.risk_tier} confidence={result.confidence} team={result.suggested_team}")
        print(f"    rationale: {result.rationale}")
        assert result.risk_tier in ("Low", "Medium", "High", "Critical")
        assert 0 <= result.confidence <= 100
        assert result.suggested_team
        assert result.suggested_sop
        assert result.rationale
