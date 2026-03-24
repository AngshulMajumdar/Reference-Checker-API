from __future__ import annotations
import re
import unicodedata

LATEX_REPLACEMENTS = {
    r'\\&': '&',
    r'\\%': '%',
    r'\\_': '_',
    r'\\-': '-',
}


def strip_outer_braces(text: str) -> str:
    text = text.strip()
    if text.startswith('{') and text.endswith('}'):
        return text[1:-1]
    return text


def delatex(text: str) -> str:
    if not text:
        return ''
    out = text
    for k, v in LATEX_REPLACEMENTS.items():
        out = out.replace(k, v)
    out = re.sub(r'\\[a-zA-Z]+\{([^{}]+)\}', r'\1', out)
    out = out.replace('{', '').replace('}', '')
    out = unicodedata.normalize('NFKD', out)
    out = ''.join(ch for ch in out if not unicodedata.combining(ch))
    return out


def normalize_title(text: str) -> str:
    text = delatex(strip_outer_braces(text)).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_author_token(text: str) -> str:
    text = delatex(text).lower()
    text = re.sub(r'[^a-z0-9\s,]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def first_author_surname(author_field: str) -> str:
    if not author_field:
        return ''
    first = author_field.split(' and ')[0].strip()
    first = normalize_author_token(first)
    if ',' in first:
        return first.split(',')[0].strip()
    return first.split()[-1].strip() if first.split() else ''
