"""Run generated examples without reading any external input files."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from strokeweaver_agent import api

if __name__ == "__main__":
    report = api.compare_policies("witness")
    print(json.dumps(api.comparison_rows(report), indent=2))
    print("Audit hash valid:", api.verify_audit(report))
    print("No model or patient task was executed.")
