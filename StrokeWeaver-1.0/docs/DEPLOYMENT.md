# Deployment

This guide deploys the **generated-only public application**. Deployment status remains pending until the owner has completed and verified it. 

## Local setup

Use a clean Python 3.11 or 3.12 environment, matching the eventual deployment version. The core declares Python ≥3.10; the documented UI dependency is pinned to Streamlit 1.55.0.

```bash
python -m venv .venv
# Activate this environment using the command appropriate to your shell.
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8810
```

Linux/macOS activation: `source .venv/bin/activate`.
Windows PowerShell activation: `.venv\Scripts\Activate.ps1`.
If activation is unavailable, invoke the environment's Python directly; do not alter a shared research environment or global execution policy to run the demo.

## Streamlit Community Cloud

Repository: [shumao469/StrokeWeaver-Agent](https://github.com/shumao469/StrokeWeaver-Agent).

The repository owner performs the account and deployment steps:

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
2. Create an app from the authorized repository and select the actual published branch.
3. Set the entrypoint to `streamlit_app.py` at the repository root.
4. Select Python 3.11 or 3.12 in advanced settings and retain `requirements.txt` with the pinned dependency.
5. Deploy, inspect build/runtime logs, and run the acceptance checklist below.
6. Record the actual resulting URL only after the app loads and the generated workflows pass. Do not guess a `streamlit.app` address.

The official deployment workflow selects repository/branch/entrypoint and allows Python-version configuration. See [Streamlit deployment documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
Place the requirements file at the root or app entrypoint directory, as described in [Streamlit dependency documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

 **Do not paste dataset decryption keys, tokens, patient data or private paths into cloud settings or repository files.** This release performs only fixed generated tasks. Hosting does not provide permission for additional data or models.

## StrokeWeaver Agent checklist

- TACTIC is labelled the internal controller.
- Generated-only and no-clinical-use boundaries are visible.
- Native workflow runs the registered fixture, displays the correct selected/stored result identity, and exports JSON/HTML/ZIP.
- Generated phantom slices are labelled as binary generated voxels, never MRI/model output.
- Shared comparison preserves all five arms, strong ties, negative controls, toy units and cost limitations.
- Input guard handles both full-ensemble and SEALS-component contracts and the fixed rejection suite without external inference.
- Task preview reports its constrained router and does not execute the request.
- There are no upload, external-path, shell, patient-task or weight-loading controls.
- Browser resizing, readable text, tab interactions and downloads are visually inspected and recorded separately.
- No private credentials, absolute research paths, protected metrics or patient content appear in pages, logs or downloads.

AppTest, CLI tests and HTTP availability are useful but do not replace actual visual browser inspection or establish clinical validation. If the browser bridge is unavailable, retain that limitation instead of labelling a schematic as a screenshot.

## Failure handling

Use another local port if 8810 is occupied by an unrelated service; do not terminate unknown processes. Keep environment/dependency changes in the dedicated virtual environment. A failed cloud build is not a failed scientific experiment; preserve the version, command and sanitized error when reporting it.

Before redeployment, run the tests in `REPRODUCIBILITY.md`, review the source diff and confirm the generated-only boundary. Changes to tools, rights, clinical input or scientific endpoints require a separate protocol and review—not only a hosting update.
