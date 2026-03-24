from __future__ import annotations
import os
from typing import List
from .base import BaseProvider
from ..models import BibEntry, CandidateRecord


class SemanticScholarProvider(BaseProvider):
    name = "semantic_scholar"

    def __init__(self, api_key: str | None = None, timeout: int = 20, min_interval: float = 0.7, cache=None):
        super().__init__(timeout=timeout, min_interval=min_interval, cache=cache)
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    def search(self, entry: BibEntry) -> List[CandidateRecord]:
        title = entry.title.strip()
        if not title:
            return []
        payload = {"title": title, "doi": (entry.doi or "").lower().strip()}
        key, cached = self._cache_get(payload)
        if cached is not None:
            return [CandidateRecord(**item) for item in cached]

        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": entry.doi.strip() if (entry.doi or '').strip() else title,
            "limit": 5,
            "fields": "title,authors,year,venue,externalIds"
        }
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        self._throttle()
        r = self.session.get(url, params=params, timeout=self.timeout, headers=headers)
        if r.status_code == 401:
            return []
        r.raise_for_status()
        items = r.json().get("data", [])
        out = []
        for item in items:
            ext = item.get("externalIds", {}) or {}
            out.append(CandidateRecord(
                source=self.name,
                title=item.get("title", ""),
                authors=[a.get("name", "") for a in item.get("authors", []) if a.get("name")],
                year=str(item.get("year", "")) if item.get("year") else None,
                venue=item.get("venue", "") or "",
                doi=ext.get("DOI"),
                pages=None,
                entry_type=None,
                raw=item,
            ))
        self._cache_set(key, [o.__dict__ for o in out])
        return out
