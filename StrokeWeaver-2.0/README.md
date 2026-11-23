# StrokeWeaver 2.0 · Evidence Workbench

StrokeWeaver 2.0 presents an auditable research workflow for generated stroke MRI inputs. Its evidence workbench lets you step through recorded execution, inspect how the system responds to a context change or interruption, and export a bound evidence report. The three included scenarios use synthetic TRACE and ADC inputs and illustrate technical verification, review referral and recovery.

[中文说明](README.zh-CN.md) · [StrokeWeaver 1.0](../StrokeWeaver-1.0/) · [StrokeWeaver 3.0](../StrokeWeaver-3.0/) · [Licensing status](../LICENSE_STATUS.md)

## What you can explore

| Scenario | Recorded workflow | Terminal | Recorded host time |
| --- | --- | --- | ---: |
| Standard run | A generated imaging task produces a native-grid artifact, the evidence checks pass and the local model receives task status through a tool call. | `STOP` | 51.73 s |
| Stale evidence | A context update changes evidence applicability and creates a technical review handoff. | `REFER` | 3.12 s |
| Interrupted run | The coordinator restarts after interruption and resumes from the verified committed artifact. | `STOP` | 30.93 s |

These times describe three individual engineering qualification runs with different execution paths. The original qualification used a frozen TinyUNet CPU forward and an isolated local Llama 3.2 3B tool exchange. The public workbench verifies and replays their recorded receipts. Its reports describe technical execution on generated inputs; clinical accuracy and clinical benefit require separate evaluation.

## Start the workbench

Use Python 3.11 or later. From the repository root, install the common dependencies and start the unified application:

```shell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Open the address printed in the terminal, typically `http://127.0.0.1:8501/`, then choose **2.0 · Evidence replay** in the navigation menu. The same application provides the 1.0 generated workflow and the 3.0 handoff dialogue.

To open 2.0 directly, run the following from the repository root:

```shell
python -m streamlit run StrokeWeaver-2.0/workbench/app.py --server.address 127.0.0.1 --server.port 18783
```

Open `http://127.0.0.1:18783/`. The workbench loads its manifest and checks the included evidence files as it opens. A successful load displays the scenario selector and the `qualification-v1` evidence receipt.

## Explore a scenario

1. Select **Standard run**, **Stale evidence** or **Interrupted run** in the sidebar.
2. Read the four summary cards for the terminal state, recorded elapsed time, model tool calls and vision forwards. `STOP` represents verified technical completion; `REFER` represents a handoff for review.
3. Open **Trace** and move the **Replay through event** slider. The table shows the recorded operations up to that event. The panels below the table describe the evidence state before and after the selected event.
4. Open **Timing** for the recorded phase times, including worker, evidence, local model, reporting, restart and applicable host time. The tab also shows the number of local model requests.
5. Open **Human review** to inspect the recorded review state. For the stale-evidence scenario, the handoff is shown as pending.
6. Open **MCP** for the bound MCP qualification, transport, protocol and verified tools. The receipt hash identifies the recorded qualification.
7. Open **Report** and choose **Download JSON evidence** to save the selected scenario's outcome, trace and timing. Expand **Evidence bindings** to inspect the hashes for the summary, independent review, scenario report, trace, probability artifact and task binding.

The interrupted-run view also displays the restart time and the recorded reuse of the committed artifact. Its evidence report includes the recovery receipt.

## Verify the release

From the repository root, run:

```shell
python -B StrokeWeaver-2.0/verify_release.py
```

The verifier loads the pinned evidence, checks the three replay paths and exercises the local MCP subprocess. A successful verification prints `qualification-v1`, the three scenario terminals and `17` passed checks out of `17`. Verification uses the Python standard library.

The [evidence manifest](evidence_manifest.json) lists the included protocol, summary, independent review, MCP qualification, scenario reports, traces and pending referral with their byte counts and SHA-256 hashes. The manifest and each listed file are checked against the release bindings before replay. The original imaging artifacts and model runtime are held separately from this receipt package.

## Connect a local MCP client

The adapter uses standard input/output transport. Configure your MCP client to run `python` with the following arguments as separate values. Use the absolute path to `mcp_stdio.py` in your checkout for the first argument:

```text
mcp_stdio.py
--attempt
qualification-v1
--summary-sha256
8baa5379a76cb4d79cc10792a4547e1ba23368f27c6ef476f2bdfe013298179b
--audit-sha256
3e25c07bb9ff682708bde1b6e32ac546cec5f3310fb1ada5a62e5ba6e34a2dd5
```

Call `get_task_status` with `{}` for the generated task status or `get_technical_handoff` with `{}` for the recorded technical review state. Both are read-only evidence queries. The [MCP transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) describes the stdio message format.

## Project files

| Path | Purpose |
| --- | --- |
| `workbench/app.py` | Streamlit scenario selection, trace, timing and export views. |
| `workbench/evidence.py` and `public_release.py` | Evidence loading, validation and the fixed release bindings. |
| `protocol.json` | Recorded generated-input workflow and qualification conditions. |
| `evidence_manifest.json` | File sizes and SHA-256 values for the included evidence. |
| `runs/qualification-v1/` | Scenario traces, reports, independent review and MCP receipt. |
| `mcp_stdio.py` | Read-only MCP adapter for task status and technical handoff. |
| `verify_release.py` | Local verification and MCP qualification entry point. |

The scenarios preserve the shared strong gate, finite-graph VOI and original risk settings recorded in the qualification. Patient-data admission, lesion scoring and formal patient comparison belong to separately authorized research workflows.
