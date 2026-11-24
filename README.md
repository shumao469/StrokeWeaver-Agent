# StrokeWeaver Agent

StrokeWeaver is a research workbench for auditable stroke-imaging workflows. (https://strokeweaver-agent.streamlit.app/)

| Workbench view | What you can do |
| --- | --- |
| **3.0 · Handoff dialogue** | Explore synthetic doctor and patient dialogues, source navigation, a versioned plan, review and handoff records, and a local timing exercise. |
| **1.0 · Generated workflow** | Run native-space quality checks and conditional repair on fixed generated inputs, compare shared policies, inspect NIfTI input checks, and export audit reports. |
| **2.0 · Evidence replay** | Inspect archived traces for standard completion, referral after evidence became stale, and interrupted-run recovery. Review the recorded timing, handoff and MCP qualification, or download the evidence report. |

[Open the hosted workbench](https://strokeweaver-agent.streamlit.app/) · [中文说明](README.zh-CN.md) · [Licensing status](LICENSE_STATUS.md) · [Security and research boundaries](SECURITY.md)

## Run locally

From the repository root, in a Python 3.11+ environment:

```shell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Open `http://127.0.0.1:8501/` and choose a version in the sidebar. The generated workflow performs fresh technical checks. The replay view verifies and displays archived evidence without rerunning the original model. The 3.0 interface uses generated demonstration cases and makes available a deterministic fallback when a local model is not configured.

## Optional local model

The dialogue workbench can call a locally operated llama.cpp server over loopback. Set `STROKEWEAVER_LLM_MODEL`, `STROKEWEAVER_LLM_WEIGHTS`, `STROKEWEAVER_LLM_WEIGHTS_SHA256`, `STROKEWEAVER_LLM_BINARY`, and `STROKEWEAVER_LLM_BINARY_SHA256` to your own model and runtime paths and verified SHA-256 values. The default port is `18788` and can be changed with `STROKEWEAVER_LLM_PORT`. Model selection is confined to read-only actions; the interface records model unavailability and uses the existing rule-based pathway.

The doctor and patient roles simulate interactions within one local session. They do not provide separate user authentication, clinical integration, diagnostic advice, or real sign-off. The study timer records an exercise and does not establish a clinician time saving.

## Deploy on Streamlit Community Cloud

Use repository `shumao469/StrokeWeaver-Agent`, branch `main`, and main file `streamlit_app.py`. Community Cloud installs the root `requirements.txt`. The public workbench does not require secrets, model weights or a GPU.

The hosted 3.0 view uses its deterministic evidence pathway when no verified model service is configured in the hosted environment. A locally configured model service is available to a locally run workbench. The separate synthetic study instrument and its assessment materials are maintained locally.

The versioned directories retain their standalone commands and verification instructions. See [StrokeWeaver 1.0](StrokeWeaver-1.0/README.md), [StrokeWeaver 2.0](StrokeWeaver-2.0/README.md), and [StrokeWeaver 3.0](StrokeWeaver-3.0/README.md) for details.

The public workbench uses generated inputs and recorded technical outcomes.
