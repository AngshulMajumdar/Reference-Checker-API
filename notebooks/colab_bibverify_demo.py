# Colab demo script
# Run this in Google Colab cell-by-cell if preferred.

!pip -q install bibtexparser rapidfuzz pandas requests unidecode transformers accelerate sentencepiece

from pathlib import Path

# Upload your .bib file in Colab or mount Drive
# from google.colab import files
# uploaded = files.upload()

INPUT_BIB = "sample_input.bib"   # change this
OUTPUT_DIR = "outputs"

# Example import after repo upload / unzip
# %cd /content/bibverify_colab
# !pip -q install -e .

from bibverify.pipeline import VerificationPipeline
from bibverify.providers.crossref_provider import CrossrefProvider
from bibverify.providers.openalex_provider import OpenAlexProvider
from bibverify.llm.judge import HuggingFaceJudge

providers = [
    CrossrefProvider(mailto="your_email@example.com"),
    OpenAlexProvider(),
]

# Pick a very small model for CPU
judge = HuggingFaceJudge(model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0")

pipeline = VerificationPipeline(
    providers=providers,
    judge=judge,
    auto_accept_threshold=0.92,
    llm_threshold=0.75,
)

result = pipeline.verify_file(INPUT_BIB, OUTPUT_DIR)
print(result)

import pandas as pd
display(pd.read_csv(Path(OUTPUT_DIR) / "report.csv"))
print((Path(OUTPUT_DIR) / "corrected.bib").read_text())
