from bibverify.pipeline import VerificationPipeline
from bibverify.providers.mock_provider import MockProvider
from bibverify.llm.judge import MockJudge
from bibverify.models import CandidateRecord, BibEntry


def build_pipeline():
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
    return VerificationPipeline(
        providers=[MockProvider(catalog)],
        judge=MockJudge(),
        auto_accept_threshold=0.85,
        llm_threshold=0.60,
        ambiguity_margin=0.04,
    )


def test_exactish_and_typo_and_unresolved(tmp_path):
    p = build_pipeline()
    bib_path = "examples/sample_input.bib"
    p.verify_file(bib_path, tmp_path)
    report = (tmp_path / "report.csv").read_text()
    corrected = (tmp_path / "corrected.bib").read_text()

    assert "doe2022theory" in corrected
    assert "maj2021pr" in corrected
    assert "Pattern Recognition with Sparse Methods" in corrected
    assert "unresolved" in report


def test_txt_upload_with_comments_and_headers(tmp_path):
    p = build_pipeline()
    txt_path = tmp_path / "input.txt"
    txt_path.write_text(
        """This is a user note before the BibTeX entries.
% another comment line
@article{maj2021pr,
  title = {Pattern recognitoin with sparse methods},
  author = {A. Majumdar},
  year = {2021}
}
""",
        encoding="utf-8",
    )
    p.verify_file(str(txt_path), tmp_path / "out_txt")
    corrected = (tmp_path / "out_txt" / "corrected.bib").read_text()
    report = (tmp_path / "out_txt" / "report.csv").read_text()

    assert "Pattern Recognition with Sparse Methods" in corrected
    assert "high_confidence_corrected" in report or "llm_adjudicated" in report


def test_ambiguous_near_miss_is_not_auto_corrected():
    catalog = {
        "Modular elliptic curves and Fermat's theorem": [
            CandidateRecord(
                source="mock",
                title="Modular elliptic curves and Fermat's last theorem",
                authors=["Andrew Wiles"],
                year="1995",
                venue="Annals of Mathematics",
                entry_type="article",
            ),
            CandidateRecord(
                source="mock2",
                title="Modular forms and elliptic curves",
                authors=["Andrew Wiles"],
                year="1993",
                venue="Inventiones Mathematicae",
                entry_type="article",
            ),
        ]
    }
    p = VerificationPipeline(
        providers=[MockProvider(catalog, min_similarity=0.6)],
        judge=MockJudge(),
        auto_accept_threshold=0.85,
        llm_threshold=0.60,
    )
    entry = BibEntry(
        entry_key="near",
        entry_type="article",
        fields={"title": "Modular elliptic curves and Fermat's theorem", "author": "Wiles, Andrew", "year": "1995"},
        raw_entry={},
    )
    corrected, decision = p.verify_entry(entry)
    assert decision.status in {"review_needed", "unresolved"}
    assert corrected.fields["title"] == entry.fields["title"]


def test_broken_entry_recovery(tmp_path):
    from bibverify.parser import load_bib_entries

    txt = """@article broken_missing_comma
  author = {Wiles, Andrew}
  title = {Modular elliptic curves and Fermat's last theorem}
  journal = {Annals of Mathematics}
  year = {1995}
}
"""
    path = tmp_path / "broken.txt"
    path.write_text(txt, encoding="utf-8")
    entries = load_bib_entries(str(path))
    assert len(entries) == 1
    assert entries[0].fields["title"] == "Modular elliptic curves and Fermat's last theorem"
