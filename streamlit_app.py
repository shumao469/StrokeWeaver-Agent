"""Compatibility entrypoint for the hosted StrokeWeaver 1.0 demo."""
from pathlib import Path
from runpy import run_path


run_path(str(Path(__file__).resolve().parent / "StrokeWeaver-1.0" / "streamlit_app.py"), run_name="__main__")
