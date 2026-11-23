"""Streamlit entrypoint for the public StrokeWeaver research workbench."""

import streamlit as st


st.set_page_config(
    page_title="StrokeWeaver Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

page = st.navigation([
    st.Page("StrokeWeaver-1.0/streamlit_app.py", title="Run a generated workflow", default=True),
    st.Page("StrokeWeaver-2.0/workbench/app.py", title="Replay audited evidence"),
])
page.run()
