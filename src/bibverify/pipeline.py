from __future__ import annotations
from pathlib import Path
import json
from collections import Counter
from typing import Tuple
import pandas as pd
from .models import BibEntry, VerificationDecision
from .parser import load_bib_entries, dump_bib_entries
from .matching.scorer import score_candidate
from .rewriter import build_change_set, apply_changes
from .reporting import write_diff_report
from .normalize import normalize_title, author_signatures


class VerificationPipeline:
    def __init__(self, providers: list, judge=None, auto_accept_threshold: float = 0.93, llm_threshold: float = 0.82, ambiguity_margin: float = 0.04, min_title_similarity: float = 0.90, min_safe_title_similarity: float = 0.95):
        self.providers = providers
        self.judge = judge
        self.auto_accept_threshold = auto_accept_threshold
        self.llm_threshold = llm_threshold
        self.ambiguity_margin = ambiguity_margin
        self.min_title_similarity = min_title_similarity
        self.min_safe_title_similarity = min_safe_title_similarity

    def _dedupe_candidates(self, scored):
        by_key = {}
        for s in scored:
            c = s.candidate
            key = (normalize_title(c.title), (c.year or "").strip(), (c.doi or "").lower().strip(), "|".join(a.lower() for a in c.authors[:3]))
            prev = by_key.get(key)
            if prev is None or s.score > prev.score:
                by_key[key] = s
        out = list(by_key.values())
        out.sort(key=lambda x: x.score, reverse=True)
        return out



    def _version_family(self, scored):
        families = []
        used = set()
        for i, s in enumerate(scored):
            if i in used:
                continue
            fam = [i]
            t1 = normalize_title(s.candidate.title)
            a1 = {x['surname'] for x in author_signatures(s.candidate.authors) if x['surname']}
            for j in range(i+1, len(scored)):
                t2 = normalize_title(scored[j].candidate.title)
                a2 = {x['surname'] for x in author_signatures(scored[j].candidate.authors) if x['surname']}
                if t1 and t2 and (t1 == t2 or (t1 in t2 or t2 in t1)) and (not a1 or not a2 or len(a1 & a2) >= max(1, min(len(a1), len(a2))//2)):
                    fam.append(j); used.add(j)
            used.add(i)
            families.append(fam)
        families.sort(key=len, reverse=True)
        return families

    def _source_disagreement(self, top_scored):
        if len(top_scored) < 2:
            return False
        titles = [normalize_title(s.candidate.title) for s in top_scored[:3] if s.score >= self.llm_threshold]
        return len(set(titles)) > 1 if titles else False

    def _is_likely_fake_or_near_miss(self, entry: BibEntry, top, scored) -> bool:
        if top is None:
            return True
        if top.features.title_similarity < self.min_title_similarity:
            return True
        if (not top.features.title_exact) and top.features.token_overlap < 0.86 and top.features.author_similarity >= 0.8 and top.features.title_similarity < 0.96:
            return True
        if entry.author and top.features.author_similarity < 0.40 and not top.features.doi_match:
            return True
        if len(scored) >= 2 and (top.score - scored[1].score) < self.ambiguity_margin and top.features.title_similarity < self.min_safe_title_similarity:
            return True
        return False

    def _select_decision(self, entry: BibEntry, scored):
        top = scored[0] if scored else None
        second = scored[1] if len(scored) > 1 else None
        ambiguity = bool(top and second and (top.score - second.score) < self.ambiguity_margin)
        disagreement = self._source_disagreement(scored)
        suspicious = self._is_likely_fake_or_near_miss(entry, top, scored)

        if top and top.features.doi_match:
            return "exact_verified", top
        if top and not suspicious and not ambiguity and not disagreement and top.score >= self.auto_accept_threshold and ((top.features.title_similarity >= self.min_safe_title_similarity and top.features.token_overlap >= 0.9) or (top.features.title_similarity >= 0.985 and top.features.author_similarity >= 0.8)):
            return "high_confidence_corrected", top
        if top and self.judge and top.score >= self.llm_threshold and (not suspicious or top.features.title_similarity >= 0.96):
            idx = self.judge.adjudicate(entry, scored[:5])
            if idx is not None:
                selected = scored[idx]
                second_score = scored[1].score if len(scored) > 1 else 0.0
                if ((selected.features.title_similarity >= self.min_safe_title_similarity and selected.features.token_overlap >= 0.9) or (selected.features.title_similarity >= 0.97 and selected.features.author_similarity >= 0.8)) and (idx == 0 or (selected.score - second_score) >= self.ambiguity_margin or len(scored) == 1):
                    return "llm_adjudicated", selected
        if scored:
            if suspicious and top.features.title_similarity < 0.9:
                return "unresolved", top
            return "review_needed", top
        return "unresolved", None

    def verify_entry(self, entry: BibEntry) -> Tuple[BibEntry, VerificationDecision]:
        candidates = []
        for p in self.providers:
            try:
                candidates.extend(p.search(entry))
            except Exception:
                pass
        scored = [score_candidate(entry, c) for c in candidates]
        scored.sort(key=lambda x: x.score, reverse=True)
        scored = self._dedupe_candidates(scored)
        status, selected = self._select_decision(entry, scored)
        top = scored[0] if scored else None
        if status in {"exact_verified", "high_confidence_corrected", "llm_adjudicated"} and selected is not None:
            changes = build_change_set(entry, selected.candidate)
            updated = apply_changes(entry, changes)
            families = self._version_family(scored[:5])
            alt = []
            if families:
                top_family = families[0]
                alt = [scored[i].candidate.title for i in top_family if scored[i].candidate.title != selected.candidate.title]
            return updated, VerificationDecision(status=status, confidence=1.0 if status == "exact_verified" else selected.score, selected_candidate=selected.candidate, reason=selected.decision_reason, change_set=changes, review_payload={"top_candidates": [s.score for s in scored[:5]], "ambiguity_margin": (selected.score - scored[1].score) if len(scored) > 1 else None, "alternate_versions": alt})
        reason = "no candidates"
        payload = None
        if top is not None:
            second_score = scored[1].score if len(scored) > 1 else None
            reason = "ambiguous or unsafe match" if status == "review_needed" else "low-confidence or likely fake/near-miss"
            payload = {"top_candidates": [s.score for s in scored[:5]], "top_titles": [s.candidate.title for s in scored[:5]], "source_counts": dict(Counter(s.candidate.source for s in scored[:5])), "score_gap": (top.score - second_score) if second_score is not None else None, "top_title_similarity": top.features.title_similarity, "top_author_similarity": top.features.author_similarity}
        return entry, VerificationDecision(status=status, confidence=(top.score if top else 0.0), selected_candidate=(top.candidate if top else None), reason=reason, change_set={}, review_payload=payload)

    def verify_file(self, input_bib: str, output_dir: str) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        entries = load_bib_entries(input_bib)
        corrected_entries = []
        rows = []
        changes_log = []
        for idx, entry in enumerate(entries, start=1):
            corrected, decision = self.verify_entry(entry)
            corrected_entries.append(corrected)
            rows.append({"entry_key": entry.entry_key, "status": decision.status, "confidence": decision.confidence, "reason": decision.reason, "selected_title": decision.selected_candidate.title if decision.selected_candidate else "", "selected_source": decision.selected_candidate.source if decision.selected_candidate else "", "n_changes": len(decision.change_set)})
            changes_log.append({"entry_key": entry.entry_key, "decision": decision.to_dict(), "original": entry.raw_entry, "corrected": corrected.raw_entry})
            if idx % 5 == 0:
                pd.DataFrame(rows).to_csv(output_dir / 'report.partial.csv', index=False)
                with open(output_dir / 'changes.partial.json', 'w', encoding='utf-8') as f:
                    json.dump(changes_log, f, indent=2, ensure_ascii=False)
        corrected_path = output_dir / "corrected.bib"
        report_path = output_dir / "report.csv"
        changes_path = output_dir / "changes.json"
        diff_path = output_dir / "diff_report.html"
        dump_bib_entries(corrected_entries, str(corrected_path))
        pd.DataFrame(rows).to_csv(report_path, index=False)
        with open(changes_path, "w", encoding="utf-8") as f:
            json.dump(changes_log, f, indent=2, ensure_ascii=False)
        write_diff_report(changes_log, str(diff_path))
        summary = pd.DataFrame(rows)["status"].value_counts().to_dict() if rows else {}
        return {"corrected_bib": str(corrected_path), "report_csv": str(report_path), "changes_json": str(changes_path), "diff_report_html": str(diff_path), "summary": summary}
