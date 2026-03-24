from pathlib import Path
from bibverify.benchmark.runner import run_benchmark


def test_benchmark_runner_outputs(tmp_path):
    files = [
        "/mnt/data/file (2).txt",
        "/mnt/data/file (3).txt",
        "/mnt/data/file (4).txt",
        "/mnt/data/file (5).txt",
        "/mnt/data/file (6).txt",
    ]
    summary = run_benchmark(files, tmp_path / "bench")
    assert summary["total_entries"] >= 40
    assert (tmp_path / "bench" / "benchmark_summary.csv").exists()
    assert (tmp_path / "bench" / "benchmark_detailed.csv").exists()
