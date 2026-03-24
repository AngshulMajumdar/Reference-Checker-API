from __future__ import annotations
import re
from unidecode import unidecode


LATEX_CLEANUPS = [
    (r"\\\([^)]+\\\)", " "),
    (r"\\\[[^\]]+\\\]", " "),
    (r"\$[^$]+\$", " "),
    (r"[{}]", " "),
    (r"\\[a-zA-Z]+\s*", " "),
    (r"[^a-zA-Z0-9\s:.,-]", " "),
]

STOPWORDS = {"a", "an", "the"}


def normalize_text(text: str) -> str:
    text = text or ""
    text = unidecode(text)
    for pat, repl in LATEX_CLEANUPS:
        text = re.sub(pat, repl, text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_title(title: str) -> str:
    title = normalize_text(title)
    title = re.sub(r"\b(a|an|the)\b", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" :.-")
    return title


def title_token_set(title: str) -> set[str]:
    return {tok for tok in normalize_title(title).split() if tok and tok not in STOPWORDS}


def normalize_author_field(author_field: str) -> list[str]:
    if not author_field:
        return []
    raw_parts = [p.strip() for p in author_field.replace("\n", " ").split(" and ")]
    out = []
    for p in raw_parts:
        if not p:
            continue
        np = normalize_text(p).replace("others", "et al")
        out.append(np)
    return out


def author_signatures(author_field: str | list[str]) -> list[dict]:
    if isinstance(author_field, list):
        raw_parts = [str(p) for p in author_field]
    else:
        raw_parts = [p.strip() for p in str(author_field or "").replace("\n", " ").split(" and ") if p.strip()]
    sigs = []
    for raw in raw_parts:
        raw_ascii = unidecode(raw)
        has_comma = "," in raw_ascii
        cleaned = re.sub(r"[{}]", " ", raw_ascii)
        cleaned = re.sub(r"\\[a-zA-Z]+\s*", " ", cleaned)
        cleaned = re.sub(r"[^a-zA-Z0-9\s,.-]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
        if not cleaned:
            continue
        if has_comma:
            left, right = [x.strip() for x in cleaned.split(",", 1)]
            surname = left.split()[-1] if left.split() else ""
            given_tokens = [t for t in right.replace(".", " ").split() if t]
            token_list = [t for t in (left + " " + right).replace(".", " ").split() if t]
        else:
            token_list = [t for t in cleaned.replace(".", " ").split() if t]
            surname = token_list[-1] if token_list else ""
            given_tokens = token_list[:-1]
        initials = "".join(t[0] for t in given_tokens if t and t[0].isalnum())
        sigs.append(
            {
                "raw": cleaned,
                "surname": surname,
                "initials": initials,
                "tokens": set(token_list),
            }
        )
    return sigs


def normalize_venue(venue: str) -> str:
    return normalize_text(venue)



def normalize_doi(doi: str) -> str:
    doi = unidecode(doi or '').strip().lower()
    doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '').replace('doi.org/', '')
    doi = re.sub(r'\s+', '', doi)
    doi = doi.strip(' ./')
    return doi


def canonical_entry_type(entry_type: str, venue: str = '', fields: dict | None = None) -> str:
    et = (entry_type or '').strip().lower()
    venue_n = normalize_venue(venue or '')
    fields = fields or {}
    if et in {'book', 'phdthesis', 'mastersthesis'}:
        return et
    if et in {'inproceedings', 'conference', 'proceedings'}:
        return 'conference'
    if et == 'article':
        if any(k in fields for k in ['booktitle']) or 'conference' in venue_n or 'proceedings' in venue_n or 'cvpr' in venue_n or 'neurips' in venue_n or 'icml' in venue_n or 'naacl' in venue_n or 'iclr' in venue_n:
            return 'conference'
        return 'journal'
    if et == 'misc' or not et or et.startswith('unknown'):
        if fields.get('eprint') or 'arxiv' in venue_n or fields.get('archiveprefix'):
            return 'preprint'
        if any(k in fields for k in ['booktitle']):
            return 'conference'
        if any(k in fields for k in ['journal']):
            return 'journal'
        return 'misc'
    return et
