# Fraud/Ops Incident Triage Copilot

A confidence-gated triage agent for Jira Service Management: incoming fraud/ops tickets
are matched against a retrieval corpus of past resolved incidents, risk-scored and
routed automatically when the model is confident, and escalated to a human via Slack
when it isn't.

Built in phases per `Fraud_Ops_Triage_Copilot_Implementation_Plan.md`. See that file for
the full phase-by-phase plan and acceptance criteria.

## Status

- [x] Phase 0 — accounts & synthetic knowledge base
- [x] Phase 1 — embedding ingestion pipeline
- [x] Phase 2 — Jira Service Management webhook listener
- [x] Phase 3 — RAG retrieval layer
- [x] Phase 4 — LLM triage classifier
- [ ] Phase 5 — auto-routing & sub-task creation
- [ ] Phase 6 — confidence-gated escalation
- [ ] Phase 7 — SLA timer & triage dashboard
- [ ] Phase 8 — end-to-end testing, demo script, polish

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your NVIDIA / Jira / Slack credentials
python3 data/generate_synthetic_kb.py
```
