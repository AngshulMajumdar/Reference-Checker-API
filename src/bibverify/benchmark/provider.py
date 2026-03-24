from __future__ import annotations
from typing import Dict, List
from ..models import CandidateRecord, BibEntry
from ..providers.mock_provider import MockProvider


def build_benchmark_provider() -> MockProvider:
    catalog: Dict[str, List[CandidateRecord]] = {
        "Modular elliptic curves and Fermat's last theorem": [
            CandidateRecord(source="gold", title="Modular elliptic curves and Fermat's last theorem", authors=["Andrew Wiles"], year="1995", venue="Annals of Mathematics", doi="10.2307/2118559", pages="443--551", entry_type="article"),
        ],
        "Perelman's proof of the Poincar\'e conjecture: a nonlinear PDE perspective": [
            CandidateRecord(source="gold", title="Perelman's proof of the Poincare conjecture: a nonlinear PDE perspective", authors=["Terence Tao"], year="2006", venue="arXiv preprint", entry_type="misc"),
        ],
        "Additive Combinatorics": [
            CandidateRecord(source="gold", title="Additive Combinatorics", authors=["Terence Tao", "Van H. Vu"], year="2006", venue="Cambridge University Press", entry_type="book"),
        ],
        "On Glaisher's Partition Theorem": [
            CandidateRecord(source="gold", title="On Glaisher's Partition Theorem", authors=["George E. Andrews", "Aritram Dhar"], year="2025", venue="arXiv preprint", entry_type="misc"),
        ],
        "Sum-difference exponents for boundedly many slopes, and rational complexity": [
            CandidateRecord(source="gold", title="Sum-difference exponents for boundedly many slopes, and rational complexity", authors=["Terence Tao"], year="2025", venue="arXiv preprint", entry_type="misc"),
        ],
        "Mathematical Analysis": [
            CandidateRecord(source="gold", title="Mathematical Analysis", authors=["Tom M. Apostol"], year="1974", venue="Addison-Wesley", entry_type="book"),
        ],
        "A method for proving Ramanujan series for $1/\pi$": [
            CandidateRecord(source="gold", title="A method for proving Ramanujan series for 1/pi", authors=["Jesus Guillera"], year="2018", venue="arXiv preprint", entry_type="misc"),
        ],
        "What is good mathematics?": [
            CandidateRecord(source="gold", title="What is good mathematics?", authors=["Terence Tao"], year="2007", venue="arXiv preprint", entry_type="misc"),
        ],
        "Small Ball and Discrepancy Inequalities": [
            CandidateRecord(source="gold", title="Small Ball and Discrepancy Inequalities", authors=["Michael T. Lacey"], year="2006", venue="arXiv preprint", entry_type="misc"),
        ],
        "Tverberg's theorem, a new proof": [
            CandidateRecord(source="gold", title="Tverberg's theorem, a new proof", authors=["Imre Barany"], year="2023", venue="arXiv preprint", entry_type="misc"),
        ],
        "Deep Learning": [
            CandidateRecord(source="gold", title="Deep Learning", authors=["Ian Goodfellow", "Yoshua Bengio", "Aaron Courville"], year="2016", venue="MIT Press", entry_type="book"),
        ],
        "Notes on Perelman's papers": [
            CandidateRecord(source="gold", title="Notes on Perelman's papers", authors=["Terence Tao"], year="2006", venue="arXiv preprint", entry_type="misc"),
        ],
        "The entropy formula for the Ricci flow and its geometric applications": [
            CandidateRecord(source="gold", title="The entropy formula for the Ricci flow and its geometric applications", authors=["Grigori Perelman"], year="2002", venue="arXiv preprint", entry_type="misc"),
        ],
        "Ring theoretic properties of certain Hecke algebras": [
            CandidateRecord(source="gold", title="Ring theoretic properties of certain Hecke algebras", authors=["Richard Taylor", "Andrew Wiles"], year="1995", venue="Annals of Mathematics", entry_type="article"),
        ],
        "Mathematical exploration and discovery at scale": [
            CandidateRecord(source="gold", title="Mathematical exploration and discovery at scale", authors=["Terence Tao"], year="2025", venue="arXiv preprint", entry_type="misc"),
        ],
        "Euler's partition theorem and generalizations": [
            CandidateRecord(source="gold", title="Euler's partition theorem and generalizations", authors=["George E. Andrews"], year="1970", venue="journal", entry_type="article"),
        ],
        "Modular forms and elliptic curves": [
            CandidateRecord(source="gold", title="Modular forms and elliptic curves", authors=["Andrew Wiles"], year="1993", venue="Inventiones Mathematicae", entry_type="article"),
        ],
    }
    return MockProvider(catalog, min_similarity=0.70)
