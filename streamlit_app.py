"""Streamlit entrypoint for the public StrokeWeaver research workbench."""

import streamlit as st
from pathlib import Path


st.set_page_config(
    page_title="StrokeWeaver Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("StrokeWeaver-3.0/handoff.py", title="3.0 · Handoff dialogue", default=True),
    st.Page("StrokeWeaver-1.0/streamlit_app.py", title="1.0 · Generated workflow"),
    st.Page("StrokeWeaver-2.0/workbench/app.py", title="2.0 · Evidence replay"),
]
study_page = Path(__file__).resolve().parent / "phase2" / "human_study_v1" / "study_app.py"
if study_page.is_file():
    pages.append(st.Page(str(study_page), title="Synthetic study · Engineering"))
page = st.navigation(pages)
page.run()
