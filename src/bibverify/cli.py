from __future__ import annotations
import argparse
from .pipeline import VerificationPipeline
from .providers.mock_provider import MockProvider
from .providers.crossref_provider import CrossrefProvider
from .providers.openalex_provider import OpenAlexProvider
from .llm.judge import MockJudge
from .models import CandidateRecord


def build_mock_pipeline():
    catalog = {
        "A theory of deep learning": [
            CandidateRecord(
                source="mock",
                title="A Theory of Deep Learning",
                authors=["Jane Doe", "John Smith"],
                year="2022",
                venue="Journal of Machine Ideas",
                doi="10.1000/jmi.2022.1",
                pages="1-10",
                entry_type="article",
            )
        ],
        "Pattern recognitoin with sparse methods": [
            CandidateRecord(
                source="mock",
                title="Pattern Recognition with Sparse Methods",
                authors=["A. Majumdar"],
                year="2021",
                venue="Pattern Analysis Letters",
                doi="10.1000/pal.2021.5",
                pages="20-30",
                entry_type="article",
            )
        ],
    }
    providers = [MockProvider(catalog)]
    judge = MockJudge()
    return VerificationPipeline(providers=providers, judge=judge, auto_accept_threshold=0.85, llm_threshold=0.60)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    verify = sub.add_parser("verify")
    verify.add_argument("--input", required=True)
    verify.add_argument("--output_dir", required=True)
    verify.add_argument("--use_mock_providers", action="store_true")
    verify.add_argument("--use_mock_judge", action="store_true")
    verify.add_argument("--mailto", default="user@example.com")

    args = parser.parse_args()
    if args.command != "verify":
        parser.print_help()
        return

    if args.use_mock_providers:
        pipeline = build_mock_pipeline()
    else:
        providers = [CrossrefProvider(mailto=args.mailto), OpenAlexProvider()]
        judge = MockJudge() if args.use_mock_judge else None
        pipeline = VerificationPipeline(providers=providers, judge=judge)

    result = pipeline.verify_file(args.input, args.output_dir)
    print(result)


if __name__ == "__main__":
    main()
