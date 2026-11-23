# StrokeWeaver 3.0 — Handoff Dialogue

An English-language research prototype for synthetic stroke handoffs. The workbench links versioned records, read-only source lookup, review, simulated sign-off and an audit receipt. A plan becomes unavailable to the simulated patient when its evidence changes.

From the repository root, install `requirements.txt` and run `python -m streamlit run streamlit_app.py`. Select **3.0 · Handoff dialogue**, or run `python -m streamlit run StrokeWeaver-3.0/handoff.py` directly.

The optional local model uses a loopback llama.cpp server. Configure `STROKEWEAVER_LLM_MODEL`, `STROKEWEAVER_LLM_WEIGHTS`, `STROKEWEAVER_LLM_WEIGHTS_SHA256`, `STROKEWEAVER_LLM_BINARY` and `STROKEWEAVER_LLM_BINARY_SHA256`. The default port is 18788 and `STROKEWEAVER_LLM_PORT` can override it. Without a verified server, the interface uses its deterministic evidence pathway and displays the model status. Model weights and executables are not bundled.

The doctor and patient roles are simulated within one session. The exercises use fictional records and do not provide patient authentication or clinical decision-making. The timing exercise records an individual rehearsal. A separate participant study is needed to assess clinician time or patient outcomes. Earlier controlled evaluations used the original Chinese-language fixtures; the translated examples are a new version and do not retain those evaluation hashes.
