from __future__ import annotations
from typing import Dict
from .models import BibEntry, CandidateRecord


def build_change_set(entry: BibEntry, cand: CandidateRecord) -> Dict[str, Dict[str, str]]:
    candidate_fields = {}
    if cand.title:
        candidate_fields["title"] = cand.title
    if cand.authors:
        candidate_fields["author"] = " and ".join(cand.authors)
    if cand.year:
        candidate_fields["year"] = str(cand.year)
    if cand.venue:
        if entry.entry_type == "article":
            candidate_fields["journal"] = cand.venue
        else:
            candidate_fields["booktitle"] = cand.venue
    if cand.doi:
        candidate_fields["doi"] = cand.doi
    if cand.pages:
        candidate_fields["pages"] = cand.pages

    changes = {}
    for k, new_v in candidate_fields.items():
        old_v = entry.fields.get(k, "")
        if (old_v or "").strip() != (new_v or "").strip():
            changes[k] = {"old": old_v, "new": new_v}
    return changes


def apply_changes(entry: BibEntry, changes: Dict[str, Dict[str, str]]) -> BibEntry:
    fields = dict(entry.fields)
    for k, diff in changes.items():
        fields[k] = diff["new"]
    return BibEntry(
        entry_key=entry.entry_key,
        entry_type=entry.entry_type,
        fields=fields,
        raw_entry={"ID": entry.entry_key, "ENTRYTYPE": entry.entry_type, **fields},
    )
