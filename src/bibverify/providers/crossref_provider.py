from __future__ import annotations
from typing import List
from .base import BaseProvider
from ..models import BibEntry, CandidateRecord


class CrossrefProvider(BaseProvider):
    name = "crossref"

    def __init__(self, mailto: str = "user@example.com", timeout: int = 20, min_interval: float = 0.3, cache=None):
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

        url = "https://api.crossref.org/works"
        params = {"rows": 5, "mailto": self.mailto}
        doi = (entry.doi or "").strip()
        if doi:
            url = f"https://api.crossref.org/works/{doi}"
        else:
            params["query.title"] = title
        self._throttle()
        r = self.session.get(url, params=params, timeout=self.timeout, headers={"User-Agent": f"bibverify/0.6 (mailto:{self.mailto})"})
        r.raise_for_status()
        body = r.json().get("message", {})
        items = [body] if doi and body else body.get("items", [])
        out = []
        for item in items:
            authors = []
            for a in item.get("author", []):
                given = a.get("given", "").strip()
                family = a.get("family", "").strip()
                name = " ".join(x for x in [given, family] if x)
                if name:
                    authors.append(name)
            title_list = item.get("title", [])
            title_text = title_list[0] if title_list else ""
            venue = ""
            for field in ["container-title", "publisher"]:
                vals = item.get(field, [])
                if isinstance(vals, list) and vals:
                    venue = vals[0]
                    break
                if isinstance(vals, str) and vals:
                    venue = vals
                    break
            year = None
            issued = item.get("issued", {}).get("date-parts", [])
            if issued and issued[0]:
                year = str(issued[0][0])
            out.append(CandidateRecord(
                source=self.name,
                title=title_text,
                authors=authors,
                year=year,
                venue=venue,
                doi=item.get("DOI"),
                pages=item.get("page"),
                entry_type=("article" if item.get("type", "").startswith("journal") else None),
                raw=item,
            ))
        self._cache_set(key, [o.__dict__ for o in out])
        return out
