# Colab-ready script for bibverify-colab

!pip -q install bibtexparser==1.4.1 rapidfuzz pandas requests huggingface_hub pytest

import os
import textwrap
from pathlib import Path

# -----------------------------
# User settings
# -----------------------------
HF_TOKEN = os.environ.get('HF_TOKEN', '')  # or set manually
HF_MODEL = 'Qwen/Qwen2.5-7B-Instruct'
USE_LLM_FOR_AMBIGUOUS = True
MAILTO = 'your_email@example.com'

# -----------------------------
# Write package files into Colab runtime
# -----------------------------
repo_root = Path('/content/bibverify_colab_runtime')
(repo_root / 'src' / 'bibverify' / 'providers').mkdir(parents=True, exist_ok=True)
(repo_root / 'src' / 'bibverify' / 'core').mkdir(parents=True, exist_ok=True)
(repo_root / 'src' / 'bibverify' / 'llm').mkdir(parents=True, exist_ok=True)

files = {
    'src/bibverify/__init__.py': "__version__='0.2.0'\n",
}
for rel, content in files.items():
    p = repo_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)

# In actual use, copy the repo files or clone from GitHub.

import sys
sys.path.insert(0, str(repo_root / 'src'))

# -----------------------------
# Install from your uploaded repo instead when using this notebook for real work.
# -----------------------------
print('Upload the repo zip or place the package under /content and then run the pipeline cells.')
print('This notebook is mainly a usage skeleton. The full package is in the downloadable zip.')

# Example Hugging Face client setup
try:
    from huggingface_hub import InferenceClient
    hf_client = InferenceClient(token=HF_TOKEN) if HF_TOKEN else None
    print('HF client ready:', hf_client is not None)
except Exception as e:
    print('HF client import failed:', e)
