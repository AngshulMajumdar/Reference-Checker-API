# bibverify_colab

A cautious BibTeX verification pipeline for free Google Colab.

## What is new in this version
- persistent JSON cache for provider responses
- request throttling and retry logic
- optional Semantic Scholar provider
- incremental partial writes during long runs
- Colab notebook saves uploads, cache, and outputs to Google Drive
- optional keep-alive snippet to reduce idle disconnects

## Recommended online stack
- Crossref as primary metadata source
- OpenAlex as consensus source
- Semantic Scholar only for ambiguous cases
- optional small Hugging Face judge on CPU for review-needed cases

## Important note on Colab disconnects
No notebook can guarantee that Colab will never disconnect. This repo reduces risk by:
- writing cache to Drive
- writing intermediate partial outputs during a run
- saving the original upload and final artifacts to Drive

## Main notebook
Use `notebooks/colab_upload_review.py`.


## Ingestion formats

The ingestion layer accepts `.bib`, `.txt`, `.pdf`, and `.docx`. For PDF/DOCX full papers, bibverify extracts the references section, parses each reference into a lightweight bibliographic record, and then runs the usual verification/correction pipeline to produce a corrected `.bib` output.

## Standalone API

Run locally:

```bash
pip install -r requirements.txt
export PYTHONPATH=$(pwd)/src
python run_api.py
```

Server docs:
- Swagger UI: `http://localhost:8000/docs`
- Health: `GET /health`
- Verify upload: `POST /api/v1/verify`

Accepted upload formats:
- `.bib`
- `.txt`
- `.pdf`
- `.docx`

Artifacts per job:
- corrected `.bib`
- `report.csv`
- `changes.json`
- `diff_report.html`
- bundled zip

Optional environment variables:
- `BIBVERIFY_STORAGE_DIR`
- `BIBVERIFY_MAILTO`
- `SEMANTIC_SCHOLAR_API_KEY`
- `BIBVERIFY_HF_MODEL`
- `BIBVERIFY_HOST`
- `BIBVERIFY_PORT`
