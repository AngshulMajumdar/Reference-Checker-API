from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class BibEntry:
    key: str
    entry_type: str
    fields: Dict[str, str]
    raw: str = ''

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
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MatchResult:
    status: str
    confidence: float
    candidate: Optional[CandidateRecord]
    reasons: List[str] = field(default_factory=list)
    field_updates: Dict[str, str] = field(default_factory=dict)
