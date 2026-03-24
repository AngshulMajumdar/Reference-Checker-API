
from pathlib import Path
from reportlab.pdfgen import canvas
from docx import Document

from bibverify.parser import load_bib_entries


def _make_sample_text() -> str:
    return """A Sample Paper\n\nIntroduction\nSome body text.\n\nReferences\n[1] Andrew Wiles. 1995. Modular elliptic curves and Fermat's last theorem. Annals of Mathematics. doi:10.2307/2118559\n[2] Terence Tao. 2006. Perelman's proof of the Poincare conjecture: a nonlinear PDE perspective. arXiv:math/0610903\n"""


def test_docx_ingestion(tmp_path: Path):
    path = tmp_path / 'paper.docx'
    doc = Document()
    for para in _make_sample_text().splitlines():
        doc.add_paragraph(para)
    doc.save(path)

    entries = load_bib_entries(str(path))
    assert len(entries) == 2
    assert 'Modular elliptic curves' in entries[0].fields.get('title', '')
    assert entries[0].fields.get('doi') == '10.2307/2118559'
    assert entries[1].fields.get('eprint') == 'math/0610903'


def test_pdf_ingestion(tmp_path: Path):
    path = tmp_path / 'paper.pdf'
    c = canvas.Canvas(str(path))
    y = 800
    for line in _make_sample_text().splitlines():
        c.drawString(72, y, line)
        y -= 16
    c.save()

    entries = load_bib_entries(str(path))
    assert len(entries) == 2
    assert entries[0].entry_key == 'ref_001'
    assert entries[1].fields.get('year') == '2006'
