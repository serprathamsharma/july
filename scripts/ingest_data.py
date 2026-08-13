import sys
import os

# Ensure backend module is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion.pipeline import run_ingestion_pipeline

if __name__ == "__main__":
    result = run_ingestion_pipeline()
    print("Ingestion Summary:", result)
