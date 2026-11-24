# StrokeWeaver 3.0 | Handoff Dialogue

StrokeWeaver 3.0 is a research workbench for exploring how evidence, review and versioned plans support a stroke handoff. It uses six fictional cases to illustrate conversations with a clinician and a simulated patient or caregiver. A clinician can inspect source records, review discrepancies, confirm a handoff and sign a plan. The patient view displays the currently signed plan, while a new record prompts renewed review.

The workbench offers three workflows for hands-on comparison. **Evidence-aware chat** uses a read-only tool selection interface and marks the applicability of retrieved records. **Retrieval chat** searches the same case records. **Fixed checklist** presents the current records by category. Each workflow operates on its own case session with the same review and sign-off rules.

The prototype is intended for research with generated cases. Clinician and patient roles are simulated within the session. The workbench supports research rehearsal and technical verification, and clinical use would require a separately approved implementation and evaluation.

## Quick start

Install Python 3.11 or later and run the following commands from the repository root:

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Open the local URL displayed by Streamlit and select **3.0 · Handoff dialogue** in the navigation. To open the 3.0 workbench directly, run:

```bash
python -m streamlit run StrokeWeaver-3.0/handoff.py --server.address 127.0.0.1
```

The included rules provide a grounded dialogue experience at startup. A verified local model can be connected for read-only tool selection as described below.

## Explore a handoff

1. In the sidebar choose **Case chat**, **Evidence-aware chat** and **Clinician**. Select **Imaging report updated** under **Synthetic case**.
2. In **Handoff chat**, enter `summary` to review the simulated handoff. Try `Find the current imaging source` and follow up with `its source?`.
3. Select **View source** in a response or use **Browse case timeline**. The source panel displays the record, its identifier, version, recorded time and current-evidence status. When applicable, it also displays the record replaced by a revision.
4. Under **Review and sign**, inspect any review items and select **Sign current plan** when the case is ready. A signature binds the plan to the current evidence snapshot.
5. In the sidebar switch **Demo role** to **Patient / caregiver** and enter `show my signed plan`. The signed plan can also be opened using **View signed plan**.
6. Switch back to **Clinician** and select **Receive simulated update**. Return to the patient view to observe the plan's review state. The clinician can inspect the new source and sign the current plan again.

The workbench keeps a separate conversation and case state for each selected workflow and case within the Streamlit session. A change of the patient plan resets the displayed patient dialogue so that the next view follows the new plan status.

The clinician can ask for multiple record categories in one turn, follow up on the source or recorded date, and request an identified record or a before-and-after comparison. The workbench resolves these questions against the case records and cites the available sources. The local model selects among bounded categories and tools, while the displayed evidence comes from the case. Patient questions are checked against the active signed plan and routed for review when the request calls for a clinician.

## Review the other scenarios

| Synthetic case | What to explore |
| --- | --- |
| **First follow-up plan missing** | A missing category enters review. Use the simulated update to add the next record and reassess the plan. |
| **Conflicting discharge lists** | Review both sources in the timeline, choose a source under **Review and sign**, and confirm the selection. |
| **Handoff awaiting confirmation** | Select **Confirm handoff** after reviewing the handoff status. |
| **Complete records and confirmed handoff** | Review the four source categories and sign the plan. |
| **Imaging report with an accepted revision** | Inspect the revision and its reference to the earlier source. |

The review panel also shows simulated referrals. Select **Acknowledge referral** to record that a review request has been received. In the simulated patient dialogue, a request to change or share a plan is routed to clinician review.

## Compare workflows in a timed rehearsal

1. Select **Synthetic research rehearsal** under **Mode**.
2. Choose a **Comparison workflow** and a **Synthetic case** in the sidebar.
3. Select **Start rehearsal**. Review the records and carry out the relevant handoff actions. Select **Record a manual correction** when an exercise includes a correction.
4. Choose the outcome in the sidebar and select **Finish and generate receipt**.
5. Select **Download timing receipt** to save the JSON receipt.

The receipt records elapsed time, the selected workflow, final plan state, pending review and referral counts, interaction counts, model and tool call counts, and evidence snapshot hashes. The exercise offers a practical way to inspect the measurement interface. A separately designed participant study is needed to establish clinician review time and outcomes.

## Connect an optional local language model

The model interface connects to a llama.cpp server on the same machine and uses constrained JSON selection for read-only evidence actions. The workbench checks the model alias, the server's model path and SHA-256 hashes for the local weights and runtime. On Windows, the following PowerShell example configures the process. Replace the example paths and alias with the files and model alias used by your server.

```powershell
$env:STROKEWEAVER_LLM_PORT = '18788'
$env:STROKEWEAVER_LLM_MODEL = 'your-model-alias'
$env:STROKEWEAVER_LLM_WEIGHTS = 'C:/models/your-model.gguf'
$env:STROKEWEAVER_LLM_BINARY = 'C:/tools/llama-server.exe'
$env:STROKEWEAVER_LLM_WEIGHTS_SHA256 = (Get-FileHash $env:STROKEWEAVER_LLM_WEIGHTS -Algorithm SHA256).Hash.ToLowerInvariant()
$env:STROKEWEAVER_LLM_BINARY_SHA256 = (Get-FileHash $env:STROKEWEAVER_LLM_BINARY -Algorithm SHA256).Hash.ToLowerInvariant()

& $env:STROKEWEAVER_LLM_BINARY --model $env:STROKEWEAVER_LLM_WEIGHTS --alias $env:STROKEWEAVER_LLM_MODEL --host 127.0.0.1 --port 18788 --n-gpu-layers 0
```

Keep the server running and launch Streamlit from another PowerShell window containing the same six environment settings. In the clinician sidebar open **Local model connection** and select **Verify loaded model**. The status shows the bound model identity. The workbench also reports when the grounded fallback handles a response.

The software uses Streamlit and Python's standard library. Model weights and the llama.cpp runtime can be obtained and configured separately. The loopback service provides the `/v1/models`, `/props` and `/v1/chat/completions` endpoints used by the adapter. Model instructions select from bounded read-only tools; the workbench checks the selection and renders source text from the case record.

## Project files

| Path | Purpose |
| --- | --- |
| `handoff.py` | English Streamlit workbench and rehearsal interface. |
| `sw3_phase2/core.py` | Synthetic case state, source versions, simulated sign-off and handoff records. |
| `sw3_phase2/followup/chat.py` | Local model adapter, retrieval and tool selection. |
| `sw3_phase2/followup/release/scope.py` | Patient request routing for plan changes and sharing. |
| `sw3_phase2/fixtures/demo_cases.json` | Six generated demonstration cases. |

See the [repository guide](../README.md) for the unified entrypoint and the guides for [1.0](../StrokeWeaver-1.0/README.md) and [2.0](../StrokeWeaver-2.0/README.md) for the imaging workflow and evidence replay. The included cases are generated examples for this workbench.
