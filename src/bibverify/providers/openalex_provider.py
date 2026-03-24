from __future__ import annotations
from typing import List
from .base import BaseProvider
from ..models import BibEntry, CandidateRecord


class OpenAlexProvider(BaseProvider):
    name = "openalex"

    def __init__(self, timeout: int = 20, min_interval: float = 0.15, cache=None, mailto: str | None = None):
        super().__init__(timeout=timeout, min_interval=min_interval, cache=cache)
        self.mailto = mailto

    def search(self, entry: BibEntry) -> List[CandidateRecord]:
        title = entry.title.strip()
        if not title:
            return []
        payload = {"title": title, "doi": (entry.doi or "").lower().strip()}
        key, cached = self._cache_get(payload)
        if cached is not None:
            return [CandidateRecord(**item) for item in cached]

        url = "https://api.openalex.org/works"
        params = {"per-page": 5}
        doi = (entry.doi or "").strip()
        if doi:
            params["filter"] = f"doi:https://doi.org/{doi.lower()}"
        else:
            params["search"] = title
        headers = {"User-Agent": f"bibverify/0.6 ({self.mailto})"} if self.mailto else None
        self._throttle()
        r = self.session.get(url, params=params, timeout=self.timeout, headers=headers)
        r.raise_for_status()
        items = r.json().get("results", [])
        out = []
        for item in items:
            authors = []
            for aa in item.get("authorships", []):
                author = aa.get("author", {})
                name = author.get("display_name", "")
                if name:
                    authors.append(name)
            primary = item.get("primary_location", {}) or {}
            source = primary.get("source", {}) or {}
            venue = source.get("display_name", "") or ""
            doi_val = item.get("doi", "")
            if doi_val.startswith("https://doi.org/"):
                doi_val = doi_val.split("https://doi.org/")[-1]
            out.append(CandidateRecord(
                source=self.name,
                title=item.get("display_name", ""),
                authors=authors,
                year=str(item.get("publication_year", "")) if item.get("publication_year") else None,
                venue=venue,
                doi=doi_val or None,
                pages=None,
                entry_type=None,
                raw=item,
            ))
        self._cache_set(key, [o.__dict__ for o in out])
        return out
