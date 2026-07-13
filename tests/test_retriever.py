"""Held-out retrieval quality test (Phase 3).

None of these 5 tickets exist in data/kb.json. Each has an expected category;
at least 4/5 must retrieve a KB entry from the matching category in their
top-3 results.
"""
from app.rag.retriever import retrieve

HELD_OUT_TICKETS = [
    {
        "title": "Customer says they never made this $89 purchase",
        "description": (
            "A customer emailed support insisting they never made a recent $89.20 "
            "charge showing up on their statement from an online electronics store. "
            "They want the charge reversed immediately."
        ),
        "expected_category": "disputed_charge_fraud",
    },
    {
        "title": "Login from unfamiliar country followed by password change",
        "description": (
            "Security monitoring flagged a login to a customer's account from a "
            "country they've never logged in from before, and minutes later the "
            "account password was changed without the customer's knowledge."
        ),
        "expected_category": "account_takeover",
    },
    {
        "title": "Merchant pushing back on a chargeback, says item was delivered",
        "description": (
            "A merchant submitted evidence disputing a chargeback, arguing that "
            "tracking shows the package was delivered and signed for at the "
            "customer's address, contradicting the customer's claim of non-receipt."
        ),
        "expected_category": "chargeback_dispute",
    },
    {
        "title": "Customer angry their card was declined for no reason",
        "description": (
            "A customer called in upset that their card kept getting declined "
            "during checkout even though they had sufficient funds and were "
            "making a normal purchase from their usual account."
        ),
        "expected_category": "false_positive_block",
    },
    {
        "title": "Widespread checkout failures across multiple merchants",
        "description": (
            "Support started receiving a flood of reports that checkout was "
            "failing with server errors across several unrelated merchants at "
            "the same time, suggesting a shared infrastructure problem."
        ),
        "expected_category": "gateway_outage",
    },
]


def test_held_out_retrieval_hit_rate():
    hits = 0
    for ticket in HELD_OUT_TICKETS:
        results = retrieve(ticket["title"], ticket["description"], k=3)
        categories = [r.record.category for r in results]
        hit = ticket["expected_category"] in categories
        print(f"{ticket['title']!r} -> {categories} (expected {ticket['expected_category']}, hit={hit})")
        if hit:
            hits += 1

    assert hits >= 4, f"Only {hits}/5 held-out tickets hit their expected category in top-3"
