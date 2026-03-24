from __future__ import annotations
import argparse
from bibverify.core.pipeline import VerificationPipeline
from bibverify.providers.crossref_provider import CrossrefProvider
from bibverify.providers.openalex_provider import OpenAlexProvider
from bibverify.llm.judge import MockJudge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input_bib')
    ap.add_argument('--out_dir', default='outputs')
    ap.add_argument('--mailto', default='user@example.com')
    ap.add_argument('--use_mock_llm', action='store_true')
    args = ap.parse_args()
    with open(args.input_bib, 'r', encoding='utf-8') as f:
        bib = f.read()
    llm = MockJudge() if args.use_mock_llm else None
    pipe = VerificationPipeline([CrossrefProvider(args.mailto), OpenAlexProvider()], llm_judge=llm)
    corrected, logs, reviews = pipe.run_text(bib)
    pipe.save_outputs(corrected, logs, reviews, args.out_dir)
    print(f'Saved outputs to {args.out_dir}')
    print(logs[['key', 'status', 'confidence']].to_string(index=False))

if __name__ == '__main__':
    main()
