from __future__ import annotations
from rapidfuzz import fuzz
from ..models import BibEntry, CandidateRecord, MatchFeatures, CandidateScore
from ..normalize import normalize_title, normalize_venue, author_signatures, title_token_set, normalize_doi, canonical_entry_type


def _author_similarity(entry_authors: list[dict], cand_authors: list[dict]) -> float:
    if not entry_authors or not cand_authors:
        return 0.0
    pair_scores = []
    for ea in entry_authors:
        best = 0.0
        for ca in cand_authors:
            score = 0.0
            if ea['surname'] and ea['surname'] == ca['surname']:
                score += 0.7
                if ea['initials'] and ca['initials']:
                    if ea['initials'] == ca['initials']:
                        score += 0.3
                    elif ea['initials'][0] == ca['initials'][0]:
                        score += 0.2
                else:
                    score += 0.1
            else:
                token_jacc = len(ea['tokens'] & ca['tokens']) / max(1, len(ea['tokens'] | ca['tokens']))
                score = max(score, token_jacc)
            best = max(best, min(score, 1.0))
        pair_scores.append(best)
    coverage = sum(pair_scores) / max(1, len(pair_scores))
    entry_surnames = {a['surname'] for a in entry_authors if a['surname']}
    cand_surnames = {a['surname'] for a in cand_authors if a['surname']}
    surname_jacc = len(entry_surnames & cand_surnames) / max(1, len(entry_surnames | cand_surnames))
    return max(coverage, surname_jacc)


def _title_metrics(entry_title: str, cand_title: str) -> tuple[float, float, float]:
    if not entry_title or not cand_title:
        return 0.0, 0.0, 0.0
    ratios = [
        fuzz.token_sort_ratio(entry_title, cand_title) / 100.0,
        fuzz.ratio(entry_title, cand_title) / 100.0,
        fuzz.partial_ratio(entry_title, cand_title) / 100.0,
    ]
    e_tokens = title_token_set(entry_title)
    c_tokens = title_token_set(cand_title)
    token_jacc = len(e_tokens & c_tokens) / max(1, len(e_tokens | c_tokens))
    containment = 1.0 if (entry_title in cand_title or cand_title in entry_title) and min(len(entry_title), len(cand_title)) >= 12 else 0.0
    sim = max(max(ratios), 0.85 * token_jacc + 0.15 * containment, containment * 0.96)
    return sim, token_jacc, containment


def build_features(entry: BibEntry, cand: CandidateRecord) -> MatchFeatures:
    entry_title = normalize_title(entry.title)
    cand_title = normalize_title(cand.title)
    entry_authors = author_signatures(entry.author)
    cand_authors = author_signatures(cand.authors)
    entry_venue = normalize_venue(entry.fields.get('journal', '') or entry.fields.get('booktitle', '') or entry.fields.get('publisher', ''))
    cand_venue = normalize_venue(cand.venue or '')

    title_similarity, token_overlap, _ = _title_metrics(entry_title, cand_title)
    author_similarity = _author_similarity(entry_authors, cand_authors)
    venue_similarity = fuzz.token_sort_ratio(entry_venue, cand_venue) / 100.0 if entry_venue and cand_venue else 0.0
    year_match = bool(entry.year and cand.year and entry.year == cand.year)
    doi_match = bool(entry.doi and cand.doi and normalize_doi(entry.doi) == normalize_doi(cand.doi))
    entry_kind = canonical_entry_type(entry.entry_type, entry.fields.get('journal', '') or entry.fields.get('booktitle', '') or entry.fields.get('publisher', ''), entry.fields)
    cand_kind = canonical_entry_type(cand.entry_type or '', cand.venue or '', {'venue': cand.venue or ''})
    compatible_types = {entry_kind, cand_kind}
    type_match = (not cand_kind) or (entry_kind == cand_kind) or compatible_types <= {'misc', 'journal'}
    return MatchFeatures(
        title_exact=(entry_title == cand_title),
        title_similarity=title_similarity,
        token_overlap=token_overlap,
        author_similarity=author_similarity,
        year_match=year_match,
        doi_match=doi_match,
        venue_similarity=venue_similarity,
        type_match=type_match,
    )


def score_candidate(entry: BibEntry, cand: CandidateRecord) -> CandidateScore:
    f = build_features(entry, cand)
    score = 0.0
    reason_bits = []

    if f.doi_match:
        score += 1.0
        reason_bits.append('doi_match')
    if f.title_exact:
        score += 0.66
        reason_bits.append('title_exact')
    else:
        score += 0.46 * f.title_similarity + 0.08 * f.token_overlap
        reason_bits.append(f'title={f.title_similarity:.2f}')

    score += 0.18 * f.author_similarity
    score += 0.08 if f.year_match else 0.0
    score += 0.07 * f.venue_similarity
    score += 0.04 if f.type_match else 0.0

    if f.title_similarity < 0.82:
        score -= 0.18
        reason_bits.append('low_title_penalty')
    elif f.title_similarity >= 0.96 and f.token_overlap >= 0.9:
        score += 0.04
        reason_bits.append('high_title_bonus')
    if entry.author and cand.authors and f.author_similarity < 0.35:
        score -= 0.08
        reason_bits.append('low_author_penalty')
    elif f.author_similarity >= 0.8:
        score += 0.03
        reason_bits.append('high_author_bonus')
    if entry.year and cand.year and not f.year_match:
        score -= 0.04
        reason_bits.append('year_mismatch_penalty')
    if entry.entry_type == 'book' and cand.pages:
        score -= 0.03
        reason_bits.append('book_pages_penalty')
    cand_kind = canonical_entry_type(cand.entry_type or '', cand.venue or '', {'venue': cand.venue or ''})
    if cand_kind == 'journal':
        score += 0.12
        reason_bits.append('tier_journal')
    elif cand_kind == 'conference':
        score += 0.06
        reason_bits.append('tier_conference')
    elif cand_kind == 'preprint':
        score += 0.00
    return CandidateScore(
        candidate=cand,
        features=f,
        score=max(0.0, min(score, 1.0)),
        decision_reason=', '.join(reason_bits),
    )
