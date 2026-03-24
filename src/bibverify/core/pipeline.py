from __future__ import annotations
from dataclasses import asdict
from typing import List, Tuple
import json
import pandas as pd
from .models import BibEntry
from .bibio import parse_bibtex, dump_bibtex
from .matcher import choose_best
from .normalize import first_author_surname

class VerificationPipeline:
    def __init__(self, providers, llm_judge=None):
        self.providers = providers
        self.llm_judge = llm_judge

    def verify_entries(self, entries: List[BibEntry]):
        corrected = []
        logs = []
        reviews = []
        for entry in entries:
            title = entry.fields.get('title', '')
            author = first_author_surname(entry.fields.get('author', ''))
            year = entry.fields.get('year', '')
            candidates = []
            for p in self.providers:
                try:
                    candidates.extend(p.search(title=title, author=author, year=year))
                except Exception as ex:
                    logs.append({'key': entry.key, 'provider': getattr(p, 'name', 'unknown'), 'event': 'provider_error', 'error': str(ex)})
            result = choose_best(entry, candidates, llm_judge=self.llm_judge)
            new_fields = dict(entry.fields)
            if result.status in {'exact_verified', 'high_confidence_corrected'} and result.field_updates:
                new_fields.update({k: v for k, v in result.field_updates.items() if v})
            corrected.append(BibEntry(key=entry.key, entry_type=entry.entry_type, fields=new_fields, raw=entry.raw))
            logs.append({
                'key': entry.key,
                'status': result.status,
                'confidence': round(result.confidence, 4),
                'reasons': result.reasons,
                'candidate': asdict(result.candidate) if result.candidate else None,
                'field_updates': result.field_updates,
            })
            if result.status in {'ambiguous_review', 'unresolved'}:
                reviews.append({
                    'key': entry.key,
                    'status': result.status,
                    'confidence': result.confidence,
                    'original_title': entry.fields.get('title', ''),
                    'suggested_title': result.candidate.title if result.candidate else '',
                })
        return corrected, pd.DataFrame(logs), pd.DataFrame(reviews)

    def run_text(self, bibtex_text: str) -> Tuple[str, pd.DataFrame, pd.DataFrame]:
        entries = parse_bibtex(bibtex_text)
        corrected, logs, reviews = self.verify_entries(entries)
        return dump_bibtex(corrected), logs, reviews

    def save_outputs(self, corrected_bib: str, logs_df, reviews_df, out_dir: str):
        import os
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'corrected.bib'), 'w', encoding='utf-8') as f:
            f.write(corrected_bib)
        logs_df.to_csv(os.path.join(out_dir, 'match_log.csv'), index=False)
        reviews_df.to_csv(os.path.join(out_dir, 'review_needed.csv'), index=False)
        with open(os.path.join(out_dir, 'change_log.jsonl'), 'w', encoding='utf-8') as f:
            for rec in logs_df.to_dict(orient='records'):
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
