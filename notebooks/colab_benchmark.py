from pathlib import Path
from google.colab import files
from bibverify.benchmark.runner import run_benchmark

uploaded = files.upload()
input_files = list(uploaded.keys())
out_dir = Path("benchmark_outputs")
summary = run_benchmark(input_files, out_dir)
print(summary)
for fname in ["benchmark_summary.csv", "benchmark_detailed.csv", "benchmark_summary.json", "benchmark_duplicates.csv"]:
    p = out_dir / fname
    if p.exists():
        files.download(str(p))
