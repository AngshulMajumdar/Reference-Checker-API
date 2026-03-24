from __future__ import annotations

from pathlib import Path
from html import escape
import difflib
from typing import List, Dict, Any

from .models import BibEntry


def bib_entry_to_text(entry: BibEntry) -> str:
    lines = [f"@{entry.entry_type}{{{entry.entry_key},"]
    for k in sorted(entry.fields):
        v = entry.fields[k]
        lines.append(f"  {k} = {{{v}}},")
    lines.append("}")
    return "\n".join(lines)


def _field_diff_html(old: str, new: str) -> str:
    if old == new:
        return escape(new)
    sm = difflib.SequenceMatcher(None, old or "", new or "")
    parts = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            parts.append(escape(new[j1:j2]))
        elif tag == "insert":
            parts.append(f'<span class="ins">{escape(new[j1:j2])}</span>')
        elif tag == "replace":
            parts.append(f'<span class="rep">{escape(new[j1:j2])}</span>')
        elif tag == "delete":
            pass
    return "".join(parts)


def write_diff_report(changes_log: List[Dict[str, Any]], path: str) -> None:
    path = Path(path)
    html = [
        '<html><head><meta charset="utf-8">',
        '<style>',
        'body{font-family:Arial,sans-serif;margin:24px;line-height:1.4;}',
        'table{border-collapse:collapse;width:100%;margin:12px 0 28px 0;}',
        'th,td{border:1px solid #ddd;padding:8px;vertical-align:top;}',
        'th{background:#f5f5f5;text-align:left;}',
        '.entry{border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:28px;}',
        '.status{font-weight:700;}',
        '.changed{background:#fff8dc;}',
        '.ins{background:#c8f7c5;font-weight:600;}',
        '.rep{background:#ffe0b2;font-weight:600;}',
        'details{margin-top:12px;}',
        '</style></head><body>',
        '<h1>BibTeX Verification Diff Report</h1>',
    ]

    for item in changes_log:
        entry_key = item["entry_key"]
        decision = item["decision"]
        status = escape(str(decision["status"]))
        confidence = float(decision.get("confidence", 0))
        changes = decision.get("change_set", {}) or {}
        original = item["original"]
        corrected = item["corrected"]
        html.append(f'<div class="entry"><h2>{escape(str(entry_key))}</h2>')
        html.append(
            f'<p><span class="status">Status:</span> {status} '
            f'&nbsp; <span class="status">Confidence:</span> {confidence:.3f}</p>'
        )
        if changes:
            html.append('<table><tr><th>Field</th><th>Original</th><th>Corrected</th></tr>')
            for field, diff in changes.items():
                old = str(diff.get("old", ""))
                new = str(diff.get("new", ""))
                html.append('<tr class="changed">')
                html.append(f'<td>{escape(str(field))}</td>')
                html.append(f'<td>{escape(old)}</td>')
                html.append(f'<td>{_field_diff_html(old, new)}</td>')
                html.append('</tr>')
            html.append('</table>')
        else:
            html.append('<p>No field changes were applied.</p>')

        html.append('<details><summary>Full entry diff</summary>')
        original_entry = BibEntry(
            entry_key=entry_key,
            entry_type=original.get("ENTRYTYPE", "misc"),
            fields={k: v for k, v in original.items() if k not in {"ID", "ENTRYTYPE"}},
            raw_entry=original,
        )
        corrected_entry = BibEntry(
            entry_key=entry_key,
            entry_type=corrected.get("ENTRYTYPE", "misc"),
            fields={k: v for k, v in corrected.items() if k not in {"ID", "ENTRYTYPE"}},
            raw_entry=corrected,
        )
        diff_html = difflib.HtmlDiff(wrapcolumn=100).make_table(
            bib_entry_to_text(original_entry).splitlines(),
            bib_entry_to_text(corrected_entry).splitlines(),
            fromdesc="Original",
            todesc="Corrected",
            context=True,
            numlines=20,
        )
        html.append(diff_html)
        html.append('</details></div>')

    html.append('</body></html>')
    path.write_text("".join(html), encoding="utf-8")
