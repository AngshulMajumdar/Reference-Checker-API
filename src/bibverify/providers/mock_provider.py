from __future__ import annotations
from typing import Dict, List
from rapidfuzz import fuzz
from .base import BaseProvider
from ..models import BibEntry, CandidateRecord
from ..normalize import normalize_title


class MockProvider(BaseProvider):
    name = "mock"

    def __init__(self, catalog: Dict[str, List[CandidateRecord]], min_similarity: float = 0.78):
        self.catalog = {normalize_title(k): v for k, v in catalog.items()}
        self.min_similarity = min_similarity

    def search(self, entry: BibEntry) -> List[CandidateRecord]:
        q = normalize_title(entry.title)
        if q in self.catalog:
            return self.catalog[q]
        best_key = None
        best_score = -1.0
        for k in self.catalog:
            s = fuzz.token_sort_ratio(q, k) / 100.0
            if s > best_score:
                best_key = k
                best_score = s
        if best_key is not None and best_score >= self.min_similarity:
            return self.catalog[best_key]
        return []
