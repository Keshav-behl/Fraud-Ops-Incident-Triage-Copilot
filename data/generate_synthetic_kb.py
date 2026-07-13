"""Generate a synthetic corpus of resolved fraud/ops tickets for the RAG knowledge base.

Run: python data/generate_synthetic_kb.py
Writes data/kb.json.
"""
import json
import random
from pathlib import Path

random.seed(42)

MERCHANTS = [
    "Amazon Marketplace", "Best Buy", "Delta Air Lines", "Uber", "DoorDash",
    "Steam", "Airbnb", "Target", "Walmart", "Apple Store", "Shopify Storefront",
    "Netflix", "PlayStation Store", "Wayfair", "Sephora", "Nike.com",
]

CITIES = [
    "Austin, TX", "Columbus, OH", "Denver, CO", "Charlotte, NC", "Seattle, WA",
    "Miami, FL", "Phoenix, AZ", "Boston, MA", "Chicago, IL", "Atlanta, GA",
]

FIRST_NAMES = ["Maria", "James", "Aisha", "Wei", "Carlos", "Priya", "Noah",
               "Fatima", "Liam", "Sofia", "Daniel", "Grace", "Omar", "Elena"]

TEAMS = {
    "disputed_charge_fraud": ["Fraud Ops L1", "Fraud Ops L2"],
    "account_takeover": ["Trust & Safety", "Fraud Ops L2"],
    "chargeback_dispute": ["Merchant Risk", "Chargeback Ops"],
    "false_positive_block": ["Fraud Ops L1", "Card Risk Team"],
    "gateway_outage": ["Payments Engineering", "Platform Reliability"],
    "card_testing": ["Card Risk Team", "Fraud Ops L2"],
}


def rand_amount(lo, hi):
    return round(random.uniform(lo, hi), 2)


def gen_disputed_charge(i):
    name = random.choice(FIRST_NAMES)
    merchant = random.choice(MERCHANTS)
    amount = rand_amount(35, 1200)
    city = random.choice(CITIES)
    tier = random.choice(["Low", "Medium", "Medium", "High"])
    title = f"Cardholder disputes ${amount:.2f} charge at {merchant}"
    description = (
        f"{name} contacted support disputing a ${amount:.2f} charge posted from {merchant}, "
        f"stating they did not authorize or recognize the transaction. Card is registered to a billing "
        f"address in {city}. No prior disputes on the account in the last 12 months."
    )
    resolution_notes = (
        f"Reviewed transaction metadata: device fingerprint and IP geolocation did not match the "
        f"cardholder's historical login pattern, consistent with unauthorized use. Provisional credit of "
        f"${amount:.2f} issued to the cardholder pending merchant response. Filed a Reg E dispute with the "
        f"card network under reason code 10.4 (other fraud - card-absent environment). Card was reissued "
        f"with a new PAN as a precaution. Merchant was notified via the dispute portal and given 30 days "
        f"to submit compelling evidence. Case closed as confirmed fraud after merchant did not respond "
        f"within the window; credit finalized."
    )
    return title, description, resolution_notes, tier, random.choice(TEAMS["disputed_charge_fraud"])


def gen_account_takeover(i):
    name = random.choice(FIRST_NAMES)
    city = random.choice(CITIES)
    new_city = random.choice([c for c in CITIES if c != city])
    tier = random.choice(["High", "High", "Critical"])
    title = f"Suspected account takeover on {name}'s account after login from new location"
    description = (
        f"Automated monitoring flagged a login to {name}'s account from {new_city}, roughly 1,800 miles "
        f"from the account's usual login region ({city}), followed within minutes by a password reset "
        f"request and an attempt to add a new payout/shipping destination."
    )
    resolution_notes = (
        f"Session was force-logged-out and the account was temporarily locked pending identity "
        f"verification. Confirmed via out-of-band phone verification that {name} did not initiate the "
        f"login or the password reset. Reverted the shipping/payout address change, rotated the account "
        f"password and API tokens, and re-enabled MFA (SMS + authenticator app). Reviewed the prior "
        f"7 days of account activity for additional unauthorized changes; none found. Added the "
        f"originating IP range to the account's risk denylist. Customer was notified of the incident "
        f"and advised to enable hardware security key as a second factor."
    )
    return title, description, resolution_notes, tier, random.choice(TEAMS["account_takeover"])


def gen_chargeback_dispute(i):
    merchant = random.choice(MERCHANTS)
    amount = rand_amount(20, 900)
    tier = random.choice(["Low", "Medium", "Medium"])
    title = f"Merchant disputes chargeback filed against {merchant}"
    description = (
        f"{merchant} submitted representment documentation contesting a ${amount:.2f} chargeback, "
        f"claiming the goods were delivered and signed for, and that the cardholder's dispute reason "
        f"(item not received) is inconsistent with their delivery and signature records."
    )
    resolution_notes = (
        f"Reviewed the merchant's compelling evidence package: signed delivery confirmation, carrier "
        f"tracking showing delivery to the billing address, and prior order history showing no pattern "
        f"of friendly fraud on this cardholder. Evidence met the network's representment threshold. "
        f"Chargeback reversed in the merchant's favor; ${amount:.2f} re-debited from the cardholder's "
        f"provisional credit. Cardholder was notified of the outcome and their right to escalate to "
        f"arbitration within 10 business days. Case logged in the merchant risk file as a resolved "
        f"first-time dispute, no pattern flag applied."
    )
    return title, description, resolution_notes, tier, random.choice(TEAMS["chargeback_dispute"])


def gen_false_positive_block(i):
    name = random.choice(FIRST_NAMES)
    merchant = random.choice(MERCHANTS)
    amount = rand_amount(50, 2500)
    tier = random.choice(["Low", "Medium"])
    title = f"Legitimate purchase blocked by fraud rule for {name}"
    description = (
        f"{name}'s ${amount:.2f} purchase at {merchant} was auto-declined by the velocity rule after "
        f"three transactions in quick succession. Customer called in frustrated, stating all three "
        f"purchases (a gift order) were intentional and made by them."
    )
    resolution_notes = (
        f"Verified the cardholder's identity via account security questions and confirmed the device "
        f"and IP matched their normal usage pattern. Confirmed all three transactions were legitimate "
        f"gift purchases placed back-to-back during a holiday sale. Released the block and manually "
        f"approved the held transactions. Added a temporary velocity-rule allowlist exception for this "
        f"account for 48 hours to prevent repeat false declines. Logged the rule trigger for the "
        f"fraud-model tuning backlog — velocity threshold may be too aggressive during flash-sale "
        f"windows. No further action needed; apologized to customer for the inconvenience."
    )
    return title, description, resolution_notes, tier, random.choice(TEAMS["false_positive_block"])


def gen_gateway_outage(i):
    tier = random.choice(["High", "Critical", "Critical"])
    duration = random.choice([8, 12, 20, 35, 50])
    pct = random.choice([15, 30, 45, 60, 80])
    title = f"Payment gateway experiencing elevated decline rate ({pct}% of transactions)"
    description = (
        f"Monitoring alerted on a spike in gateway timeouts starting at {random.choice(['02:14','09:47','14:22','19:03'])} UTC, "
        f"with roughly {pct}% of authorization requests failing with 5xx or timeout errors over a "
        f"{duration}-minute window. Multiple merchants reported checkout failures simultaneously."
    )
    resolution_notes = (
        f"Confirmed the root cause was a degraded upstream connection to the card network's "
        f"authorization endpoint following a routing change on the network's side. Engaged the payment "
        f"processor's incident channel and failed traffic over to the secondary acquiring connection. "
        f"Decline rate returned to baseline (<2%) within {duration} minutes of failover. Ran a "
        f"reconciliation job afterward to identify and retry transactions that failed during the window "
        f"but had funds authorized on the issuer side. Posted a status-page update and an internal "
        f"postmortem action item to add automatic failover detection instead of manual triage."
    )
    return title, description, resolution_notes, tier, random.choice(TEAMS["gateway_outage"])


def gen_card_testing(i):
    tier = random.choice(["High", "Critical"])
    count = random.choice([40, 75, 120, 200, 350])
    amount = round(random.uniform(0.5, 2.0), 2)
    title = f"Card-testing attack detected: {count} small-value auths from single IP range"
    description = (
        f"Fraud detection flagged {count} authorization attempts for small amounts (~${amount:.2f} each) "
        f"originating from a narrow IP range within a 10-minute span, targeting sequential/randomly "
        f"generated card numbers — a signature consistent with automated card-testing (BIN attack) "
        f"activity rather than legitimate checkout traffic."
    )
    resolution_notes = (
        f"Blocked the originating IP range and associated device fingerprints at the WAF/gateway layer. "
        f"Enabled a temporary CAPTCHA challenge on the checkout endpoint for the affected merchant "
        f"category to slow further automated attempts. Cross-referenced the tested card numbers with "
        f"the issuer's compromised-BIN list and flagged matches for proactive reissuance. Reported the "
        f"attack pattern to the card network's fraud intelligence unit. No successful fraudulent "
        f"transactions were confirmed to have gone through; all testing attempts were declined by the "
        f"velocity and low-amount heuristic rules. Added the attack signature to the standing detection "
        f"ruleset."
    )
    return title, description, resolution_notes, tier, random.choice(TEAMS["card_testing"])


GENERATORS = {
    "disputed_charge_fraud": gen_disputed_charge,
    "account_takeover": gen_account_takeover,
    "chargeback_dispute": gen_chargeback_dispute,
    "false_positive_block": gen_false_positive_block,
    "gateway_outage": gen_gateway_outage,
    "card_testing": gen_card_testing,
}

RECORDS_PER_CATEGORY = 15


def main():
    records = []
    counter = 1
    for category, gen_fn in GENERATORS.items():
        for i in range(RECORDS_PER_CATEGORY):
            title, description, resolution_notes, tier, team = gen_fn(i)
            records.append({
                "id": f"KB-{counter:04d}",
                "title": title,
                "description": description,
                "resolution_notes": resolution_notes,
                "risk_tier": tier,
                "resolved_by_team": team,
                "category": category,
            })
            counter += 1

    random.shuffle(records)

    out_path = Path(__file__).parent / "kb.json"
    out_path.write_text(json.dumps(records, indent=2))
    print(f"Wrote {len(records)} records to {out_path}")
    print(f"Categories: {sorted(GENERATORS.keys())}")


if __name__ == "__main__":
    main()
