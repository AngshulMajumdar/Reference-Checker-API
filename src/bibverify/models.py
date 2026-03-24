from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class BibEntry:
    entry_key: str
    entry_type: str
    fields: Dict[str, str]
    raw_entry: Dict[str, Any]

    @property
    def title(self) -> str:
        return self.fields.get("title", "").strip()

    @property
    def year(self) -> str:
        return self.fields.get("year", "").strip()

    @property
    def author(self) -> str:
        return self.fields.get("author", "").strip()

    @property
    def doi(self) -> str:
        return self.fields.get("doi", "").strip()


@dataclass
class CandidateRecord:
    source: str
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[str] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    pages: Optional[str] = None
    entry_type: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchFeatures:
    title_exact: bool
    title_similarity: float
    token_overlap: float
    author_similarity: float
    year_match: bool
    doi_match: bool
    venue_similarity: float
    type_match: bool


@dataclass
class CandidateScore:
    candidate: CandidateRecord
    features: MatchFeatures
    score: float
    decision_reason: str = ""


@dataclass
class VerificationDecision:
    status: str
    confidence: float
    selected_candidate: Optional[CandidateRecord]
    reason: str
    change_set: Dict[str, Dict[str, str]] = field(default_factory=dict)
    review_payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        return out
