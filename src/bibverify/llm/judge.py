from __future__ import annotations
import json
from typing import List, Optional
from ..models import BibEntry, CandidateScore


class BaseJudge:
    def adjudicate(self, entry: BibEntry, scored_candidates: List[CandidateScore]) -> Optional[int]:
        raise NotImplementedError


class MockJudge(BaseJudge):
    def adjudicate(self, entry: BibEntry, scored_candidates: List[CandidateScore]) -> Optional[int]:
        if not scored_candidates:
            return None
        return 0


class HuggingFaceJudge(BaseJudge):
    def __init__(self, model_name: str, max_new_tokens: int = 128):
        from transformers import pipeline
        self.pipe = pipeline(
            "text-generation",
            model=model_name,
            tokenizer=model_name,
            device=-1,
        )
        self.max_new_tokens = max_new_tokens

    def adjudicate(self, entry: BibEntry, scored_candidates: List[CandidateScore]) -> Optional[int]:
        if not scored_candidates:
            return None
        compact = []
        for i, sc in enumerate(scored_candidates[:5]):
            compact.append({
                "idx": i,
                "title": sc.candidate.title,
                "authors": sc.candidate.authors[:5],
                "year": sc.candidate.year,
                "venue": sc.candidate.venue,
                "doi": sc.candidate.doi,
                "score": round(sc.score, 3),
            })
        prompt = (
            "You are matching one BibTeX entry to the correct scholarly record.\n"
            "Return JSON only with fields: selected_idx, confidence, reason, safe_fields.\n"
            "If no candidate is reliable, selected_idx should be -1.\n\n"
            f"BibTeX entry:\n{json.dumps(entry.raw_entry, ensure_ascii=False)}\n\n"
            f"Candidates:\n{json.dumps(compact, ensure_ascii=False)}\n"
        )
        out = self.pipe(prompt, max_new_tokens=self.max_new_tokens, do_sample=False)[0]["generated_text"]
        answer = out[len(prompt):].strip()
        try:
            parsed = json.loads(answer)
            idx = int(parsed.get("selected_idx", -1))
            if idx < 0 or idx >= len(scored_candidates):
                return None
            return idx
        except Exception:
            return None
