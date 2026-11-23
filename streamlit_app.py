"""Streamlit entrypoint for the public StrokeWeaver research workbench."""

import streamlit as st


st.set_page_config(
    page_title="StrokeWeaver Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

page = st.navigation([
    st.Page("StrokeWeaver-1.0/streamlit_app.py", title="1.0 · Generated workflow", default=True),
    st.Page("StrokeWeaver-2.0/workbench/app.py", title="2.0 · Evidence replay"),
    st.Page("StrokeWeaver-3.0/handoff.py", title="3.0 · Handoff dialogue"),
])
page.run()
