"""Compatibility entrypoint for the StrokeWeaver 1.0 CLI."""
from pathlib import Path
from runpy import run_path


if __name__ == "__main__":
    run_path(str(Path(__file__).resolve().parent / "StrokeWeaver-1.0" / "run.py"), run_name="__main__")
