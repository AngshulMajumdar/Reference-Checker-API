from __future__ import annotations
from typing import List, Optional
from rapidfuzz import fuzz
from .models import BibEntry, CandidateRecord, MatchResult
from .normalize import normalize_title, first_author_surname

TRUST_WEIGHTS = {
    'crossref': 0.07,
    'openalex': 0.06,
    'dblp': 0.08,
    'semantic_scholar': 0.05,
}


def score_candidate(entry: BibEntry, cand: CandidateRecord) -> tuple[float, list[str]]:
    reasons = []
    score = 0.0
    e_title = normalize_title(entry.fields.get('title', ''))
    c_title = normalize_title(cand.title)
    if not e_title or not c_title:
        return 0.0, ['missing title']
    title_ratio = fuzz.ratio(e_title, c_title) / 100.0
    token_ratio = fuzz.token_set_ratio(e_title, c_title) / 100.0
    score += 0.35 * title_ratio + 0.25 * token_ratio
    if e_title == c_title:
        score += 0.12
        reasons.append('title_exact=1')
    reasons.append(f'title_ratio={title_ratio:.3f}')
    reasons.append(f'token_ratio={token_ratio:.3f}')
    e_doi = (entry.fields.get('doi') or '').strip().lower().replace('https://doi.org/', '')
    c_doi = (cand.doi or '').strip().lower().replace('https://doi.org/', '')
    if e_doi and c_doi and e_doi == c_doi:
        score += 0.35
        reasons.append('doi_exact=1')
    e_year = (entry.fields.get('year') or '').strip()
    if e_year and cand.year and e_year == str(cand.year):
        score += 0.08
        reasons.append('year_exact=1')
    e_surname = first_author_surname(entry.fields.get('author', ''))
    c_surname = ''
    if cand.authors:
        c_surname = cand.authors[0].split()[-1].lower()
    if e_surname and c_surname and e_surname == c_surname:
        score += 0.08
        reasons.append('first_author_exact=1')
    venue = (entry.fields.get('journal') or entry.fields.get('booktitle') or '').lower()
    cvenue = (cand.venue or '').lower()
    if venue and cvenue:
        venue_ratio = fuzz.token_set_ratio(venue, cvenue) / 100.0
        score += 0.07 * venue_ratio
        reasons.append(f'venue_ratio={venue_ratio:.3f}')
    score += TRUST_WEIGHTS.get(cand.source, 0.03)
    reasons.append(f'source_weight={TRUST_WEIGHTS.get(cand.source, 0.03):.3f}')
    return min(score, 1.0), reasons


def choose_best(entry: BibEntry, candidates: List[CandidateRecord], llm_judge=None) -> MatchResult:
    if not candidates:
        return MatchResult(status='unresolved', confidence=0.0, candidate=None, reasons=['no candidates'])
    scored = []
    for c in candidates:
        s, reasons = score_candidate(entry, c)
        scored.append((s, c, reasons))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, top_cand, top_reasons = scored[0]
    updates = build_updates(entry, top_cand)
    if top_score >= 0.92:
        return MatchResult(status='exact_verified', confidence=top_score, candidate=top_cand, reasons=top_reasons, field_updates=updates)
    if top_score >= 0.82:
        return MatchResult(status='high_confidence_corrected', confidence=top_score, candidate=top_cand, reasons=top_reasons, field_updates=updates)
    if top_score >= 0.68 and llm_judge is not None:
        judge_payload = llm_judge.judge(entry, [x[1] for x in scored[:3]])
        idx = judge_payload.get('chosen_index')
        decision = judge_payload.get('decision')
        if idx is not None and decision in {'accept', 'review'} and idx < min(3, len(scored)):
            chosen = scored[idx][1]
            updates = build_updates(entry, chosen)
            status = 'high_confidence_corrected' if decision == 'accept' else 'ambiguous_review'
            return MatchResult(status=status, confidence=top_score, candidate=chosen,
                               reasons=top_reasons + [f'llm_decision={decision}'], field_updates=updates)
    return MatchResult(status='ambiguous_review', confidence=top_score, candidate=top_cand, reasons=top_reasons, field_updates=updates)


def build_updates(entry: BibEntry, cand: CandidateRecord) -> dict[str, str]:
    updates = {}
    if cand.title:
        updates['title'] = '{' + cand.title + '}'
    if cand.year:
        updates['year'] = str(cand.year)
    if cand.doi:
        updates['doi'] = cand.doi
    if cand.pages:
        updates['pages'] = cand.pages
    if cand.venue:
        if entry.entry_type == 'article':
            updates['journal'] = cand.venue
        else:
            updates['booktitle'] = cand.venue
    if cand.authors:
        updates['author'] = ' and '.join(cand.authors)
    return updates
