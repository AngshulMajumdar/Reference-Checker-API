from __future__ import annotations
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from .models import BibEntry


def parse_bibtex(text: str):
    db = bibtexparser.loads(text)
    out = []
    for e in db.entries:
        key = e.get('ID', '')
        entry_type = e.get('ENTRYTYPE', '')
        fields = {k: v for k, v in e.items() if k not in ('ID', 'ENTRYTYPE')}
        out.append(BibEntry(key=key, entry_type=entry_type, fields=fields, raw=''))
    return out


def dump_bibtex(entries):
    db = BibDatabase()
    db.entries = []
    for entry in entries:
        row = {'ID': entry.key, 'ENTRYTYPE': entry.entry_type}
        row.update(entry.fields)
        db.entries.append(row)
    writer = BibTexWriter()
    writer.indent = '  '
    writer.order_entries_by = None
    return writer.write(db)
