# StrokeWeaver 2.0 

[中文说明](README.zh-CN.md) · [StrokeWeaver 1.0](../StrokeWeaver-1.0/) · [Licensing status](../LICENSE_STATUS.md)

Explore the audited execution of three fixed generated MRI scenarios. The original local qualification linked a `TaskSpec`, a fresh frozen TinyUNet CPU forward, native-grid artifact verification, an isolated local Llama tool exchange, and technical completion or human referral. This distribution replays the original receipts, validates their hashes, and serves two read-only MCP queries. The original model runtime and weights are kept separately.

| Generated scenario | Terminal | End-to-end host time |
| --- | --- | ---: |
| Standard run | `STOP` after one status-tool call and two local LLM requests | 51.73 s |
| Stale evidence | `REFER` with pending technical review and zero local LLM requests | 3.12 s |
| Interrupted coordinator | `STOP` after reusing the verified artifact, with zero duplicate vision forwards or charges | 30.93 s |

These are recorded engineering qualification times. The routes differ in startup and tool dispatch, so their elapsed times are not a speedup benchmark. No patient inputs, protected labels or clinical performance results are part of the distribution.

## Run the local workbench

From `StrokeWeaver-2.0`, with Python 3.11 or later in an isolated environment:

```shell
python -m pip install -r workbench/requirements.txt
python -m streamlit run workbench/app.py --server.address 127.0.0.1 --server.port 18783 --browser.gatherUsageStats false
```

Open `http://127.0.0.1:18783/` on the same machine. Select a scenario to inspect its event trace, timing, technical review state and MCP qualification, or download its report as JSON. The recorded referral remains read-only in the public workbench.

## Verify the evidence or use MCP

```shell
python -B verify_release.py
```

Verification uses the standard library. It checks all 11 pinned original documents, validates the three replay paths and runs a real MCP subprocess. For a local MCP client, use `python` as the command and pass these arguments as separate values. Set the first argument to the full path to `mcp_stdio.py` in your checkout.

```text
mcp_stdio.py
--attempt
qualification-v1
--summary-sha256
8baa5379a76cb4d79cc10792a4547e1ba23368f27c6ef476f2bdfe013298179b
--audit-sha256
3e25c07bb9ff682708bde1b6e32ac546cec5f3310fb1ada5a62e5ba6e34a2dd5
```

Both `get_task_status` and `get_technical_handoff` accept `{}` and return generated evidence summaries. See the [MCP stdio specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

The [evidence manifest](evidence_manifest.json) identifies the original protocol, summary, independent audit, MCP qualification, scenario reports, traces and pending referral. It verifies the included bytes. The local audit's referenced imaging artifacts and private runtime are outside the replay package. The shared strong gate, complete finite-graph VOI, and original risk settings were retained, with patient admission and formal evaluation separate from this qualification.
