"""Use the existing generated-only native-grid tool through its fixed entry point."""

from pathlib import Path
import sys


def run_generated_qc(fixture="centimeter_encoded"):
    package = Path(__file__).resolve().parents[2] / "StrokeWeaver-1.0" / "src"
    if str(package) not in sys.path:
        sys.path.insert(0, str(package))
    from strokeweaver_agent import api

    source = api.run_demo(fixture)
    if not api.verify_audit(source):
        raise ValueError("The generated imaging tool audit hash did not verify.")
    return source
