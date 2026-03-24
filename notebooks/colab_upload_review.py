# Colab-ready upload/review/download workflow for bibverify
# CPU-safe, cached, and resilient to reconnects because intermediate outputs are written to Drive.

!pip -q install bibtexparser==1.4.1 rapidfuzz pandas requests transformers accelerate sentencepiece python-docx PyMuPDF

import os, sys, json, time
from pathlib import Path
from IPython.display import display, HTML, Javascript

# Optional keep-alive. This reduces idle disconnects, but Colab can still stop long sessions.
def activate_keepalive(interval_ms=60000):
    display(Javascript(f"""
    function ClickConnect() {{
      const btn = document.querySelector('colab-connect-button') || document.querySelector('#connect');
      if (btn) btn.click();
    }}
    setInterval(ClickConnect, {interval_ms});
    """))

activate_keepalive()

from google.colab import drive, files
print('Mounting Google Drive for persistent cache and outputs...')
drive.mount('/content/drive')

REPO_ROOT = Path('/content/bibverify_colab')
sys.path.insert(0, str(REPO_ROOT / 'src'))

from bibverify.pipeline import VerificationPipeline
from bibverify.cache import JsonCache
from bibverify.providers.crossref_provider import CrossrefProvider
from bibverify.providers.openalex_provider import OpenAlexProvider
from bibverify.providers.semantic_scholar_provider import SemanticScholarProvider
from bibverify.llm.judge import HuggingFaceJudge

CACHE_DIR = Path('/content/drive/MyDrive/bibverify_cache')
OUTPUT_ROOT = Path('/content/drive/MyDrive/bibverify_runs')
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
cache = JsonCache(CACHE_DIR / 'provider_cache.json')

USE_LLM = False
USE_SEMANTIC_SCHOLAR = False
HF_MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
MAILTO = 'user@example.com'  # change this

providers = [
    CrossrefProvider(mailto=MAILTO, cache=cache),
    OpenAlexProvider(mailto=MAILTO, cache=cache),
]
if USE_SEMANTIC_SCHOLAR:
    providers.append(SemanticScholarProvider(cache=cache))
judge = HuggingFaceJudge(HF_MODEL) if USE_LLM else None
pipeline = VerificationPipeline(providers=providers, judge=judge, auto_accept_threshold=0.92, llm_threshold=0.75)

print('Choose a .bib, .txt, .pdf, or .docx file. For PDFs/DOCX, bibverify will extract the references section and emit corrected BibTeX.')
uploaded = files.upload()
assert uploaded, 'No file uploaded.'
input_name = next(iter(uploaded.keys()))
input_path = Path('/content') / input_name
run_dir = OUTPUT_ROOT / f"run_{int(time.time())}_{input_path.stem.replace(' ', '_')}"
run_dir.mkdir(parents=True, exist_ok=True)

# Save original upload for traceability
(run_dir / input_path.name).write_bytes(input_path.read_bytes())

result = pipeline.verify_file(str(input_path), str(run_dir))
print('Summary:', result['summary'])
print('Outputs saved to:', run_dir)

html_path = Path(result['diff_report_html'])
display(HTML(html_path.read_text(encoding='utf-8')))

files.download(result['corrected_bib'])
files.download(result['report_csv'])
files.download(result['changes_json'])
files.download(result['diff_report_html'])
