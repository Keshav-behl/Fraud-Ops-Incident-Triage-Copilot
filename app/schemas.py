from typing import Literal
from pydantic import BaseModel, Field


class KBRecord(BaseModel):
    id: str
    title: str
    description: str
    resolution_notes: str
    risk_tier: Literal["Low", "Medium", "High", "Critical"]
    resolved_by_team: str
    category: str


class RetrievedRecord(BaseModel):
    record: KBRecord
    similarity: float


class TriageResult(BaseModel):
    risk_tier: Literal["Low", "Medium", "High", "Critical"]
    confidence: float = Field(ge=0, le=100)
    suggested_team: str
    suggested_sop: str
    rationale: str
