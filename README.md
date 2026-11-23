# StrokeWeaver Agent

StrokeWeaver is a research workbench for auditable stroke-imaging workflows. One Streamlit app brings the two releases into a single interface.

| Workbench view | What you can do |
| --- | --- |
| **Run a generated workflow** | Run native-space quality checks and conditional repair on fixed generated inputs, compare shared policies, inspect NIfTI input checks, and export audit reports. |
| **Replay audited evidence** | Inspect archived traces for standard completion, referral after evidence became stale, and interrupted-run recovery. Review the recorded timing, handoff and MCP qualification, or download the evidence report. |

[Open the hosted workbench](https://strokeweaver-agent.streamlit.app/) · [中文说明](README.zh-CN.md) · [Licensing status](LICENSE_STATUS.md) · [Security and research boundaries](SECURITY.md)

## Run locally

From the repository root, in a Python 3.11+ environment:

```shell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Open `http://127.0.0.1:8501/` and choose a view in the sidebar. The generated workflow performs fresh technical checks. The replay view verifies and displays archived evidence without rerunning the original model.

## Deploy on Streamlit Community Cloud

Use repository `shumao469/StrokeWeaver-Agent`, branch `main`, and main file `streamlit_app.py`. Community Cloud installs the root `requirements.txt`. The public workbench does not require secrets, model weights or a GPU.

The versioned directories retain their standalone commands and verification instructions. See [StrokeWeaver 1.0](StrokeWeaver-1.0/README.md) and [StrokeWeaver 2.0](StrokeWeaver-2.0/README.md) for details.

The public software uses generated inputs and recorded technical outcomes. The separate [supplementary information and editable figures](manuscript/draft/) include a de-identified public SOOP image example and published DeepISLES figure crops with source and license information. The workbench runs generated inputs only.
