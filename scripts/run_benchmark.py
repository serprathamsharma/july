import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.benchmark import run_benchmark_suite

if __name__ == "__main__":
    results = asyncio.run(run_benchmark_suite())
