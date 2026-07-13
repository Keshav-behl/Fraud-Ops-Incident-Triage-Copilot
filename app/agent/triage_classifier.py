import json

import openai
from pydantic import ValidationError

from app.llm.nvidia_client import chat
from app.rag.retriever import retrieve
from app.schemas import RetrievedRecord, TriageResult

SYSTEM_PROMPT = """You are a fraud/ops triage classifier for a payments company.

You will be given an incoming support ticket and a list of similar past
resolved tickets (precedents) retrieved from a knowledge base. Using ONLY the
ticket and the given precedents, produce a triage decision.

Respond with ONLY a single JSON object (no markdown fences, no commentary)
matching exactly this shape:
{
  "risk_tier": "Low" | "Medium" | "High" | "Critical",
  "confidence": <number 0-100>,
  "suggested_team": "<team name>",
  "suggested_sop": "<short suggested standard operating procedure>",
  "rationale": "<explanation that explicitly references at least one of the given precedents by its id or title>"
}

confidence should reflect how well the precedents match this ticket and how
unambiguous the categorization is. Ambiguous or blended cases (e.g. a ticket
that could plausibly belong to two different precedent categories) must get
a LOWER confidence score, not a forced pick.
"""


def _format_precedents(precedents: list[RetrievedRecord]) -> str:
    lines = []
    for p in precedents:
        r = p.record
        lines.append(
            f"- id={r.id} | title={r.title!r} | risk_tier={r.risk_tier} | "
            f"team={r.resolved_by_team} | similarity={p.similarity:.3f}\n"
            f"  description: {r.description}\n"
            f"  resolution_notes: {r.resolution_notes}"
        )
    return "\n".join(lines)


def _build_user_prompt(ticket_title: str, ticket_description: str, precedents: list[RetrievedRecord]) -> str:
    return (
        f"Incoming ticket:\n"
        f"title: {ticket_title}\n"
        f"description: {ticket_description}\n\n"
        f"Retrieved precedents:\n{_format_precedents(precedents)}\n\n"
        f"Return the JSON triage decision now."
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    return json.loads(text[start : end + 1])


def classify(ticket_title: str, ticket_description: str, k: int = 4) -> TriageResult:
    precedents = retrieve(ticket_title, ticket_description, k=k)
    user_prompt = _build_user_prompt(ticket_title, ticket_description, precedents)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    for attempt in range(2):
        try:
            raw = chat(messages, temperature=0.2)
        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            last_error = e
            continue  # transient network issue, retry with the same messages

        try:
            data = _extract_json(raw)
            return TriageResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": (
                    f"That response was invalid ({e}). Respond again with ONLY the "
                    f"corrected JSON object, no other text."
                ),
            })

    raise ValueError(f"Failed to get valid TriageResult after retry: {last_error}")
