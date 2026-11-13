"""Local Streamlit workbench for independently audited StrokeWeaver replays."""

import json
from pathlib import Path
import sys

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from public_release import load_public_replay
from workbench.evidence import EvidenceDenied


TITLES = {"normal": "Standard run", "stale": "Stale evidence", "recovery": "Interrupted run"}
PHASE_LABELS = {"worker": "Vision worker", "evidence": "Evidence checks", "llm": "Local model",
                "report": "Report", "recovery": "Restart", "other": "Other coordinator time",
                "host_residual": "Host startup and collection"}
STYLE = """
<style>
[data-testid=stMainBlockContainer] {max-width: 1150px; padding-top: 2.65rem;}
[data-testid=stSidebarContent] {border-right: 1px solid #273b49;}
[data-testid=stMetric] {background: #14242e; border: 1px solid #2a404f; border-radius: 7px; padding: 0.9rem 1rem;}
[data-testid=stMetricLabel] {color: #b8c8cf;}
[data-testid=stMetricValue] {color: #def3ef;}
.sw-kicker {color:#80d5c2; font-family:monospace; letter-spacing:.1em; font-size:.75rem; margin:0 0 .18rem;}
.sw-divider {border-top:1px solid #2a404f; margin:1rem 0;}
</style>
"""


def step_detail(event):
    fields = {
        "state": "State", "evidence_state": "Evidence", "status": "Status", "applicable": "Applicable",
        "action": "Action", "decision": "Decision", "reason": "Reason", "tool": "Tool", "attempt": "Attempt",
        "artifact_reused": "Artifact reused", "terminal": "Terminal", "human_state": "Review",
        "normalized_action": "Result", "returncode": "Exit code",
    }
    return " · ".join(f"{label} {event[key]}" for key, label in fields.items() if key in event)


def event_state(event):
    if "applicable" in event:
        return "Evidence applicable" if event["applicable"] else "Evidence invalidated"
    if event.get("artifact_reused") is True:
        return "Verified artifact reused"
    if event.get("returncode") == -9:
        return "Owned coordinator exited after SIGKILL"
    return next((str(event[key]) for key in ("evidence_state", "state", "after", "status", "terminal")
                 if key in event), "Recorded")


def display_timeline(scenario):
    st.subheader("Execution trace")
    events = scenario["trace"]
    default = next((event["step"] for event in events if event["event"] == "EVIDENCE_INVALIDATED"), len(events))
    active = st.select_slider("Replay through event", options=list(range(1, len(events) + 1)), value=default,
                              key=scenario["scenario"] + "_step")
    st.progress(active / len(events), text=f"Event {active} of {len(events)}")
    rows = [{"Step": e["step"], "Operation": e["event"], "Evidence": step_detail(e)}
            for e in events[:active]]
    st.dataframe(rows, hide_index=True, width="stretch", height=min(310, 36 * len(rows) + 40))
    selected = events[active - 1]
    preceding = next((event for event in reversed(events[:active - 1]) if "applicable" in event), None)
    preceding = preceding or (events[active - 2] if active > 1 else None)
    left, right = st.columns(2)
    left.markdown("**Before event**")
    left.caption(f"{preceding['event']} · {event_state(preceding)}" if preceding else "Start of archived trace")
    right.markdown("**After event**")
    right.caption(f"{selected['event']} · {event_state(selected)}")
    detail = step_detail(selected)
    if detail:
        st.caption(detail)


def show_review(scenario):
    st.subheader("Human review")
    if scenario["human_state"] == "NOT_REQUIRED":
        st.success("The replay completed without a human-review request.")
        return
    st.warning("Referral pending in the audited run.")
    st.caption("The public replay displays the archived handoff state.")


def show_mcp(replay):
    st.subheader("MCP verification")
    mcp = replay["mcp"]
    if mcp is None:
        st.info("A bound MCP qualification receipt is pending for this run.")
        return
    st.success("The local MCP qualification passed.")
    st.markdown(f"**Transport** {mcp['transport']} · **Protocol** {mcp['protocol_version']}")
    st.markdown("**Verified tools**")
    st.write("\n".join(f"- {name}" for name in mcp["tools"]))
    st.caption(f"{mcp['checks']} recorded checks passed. The MCP receipt is bound to this run and independent review.")
    st.code(mcp["receipt_sha256"], language=None)


def show_export(replay, scenario):
    st.subheader("Evidence report")
    st.write("Download this scenario’s audited outcome, timing and trace.")
    payload = {key: replay[key] for key in ("attempt", "scope", "summary_sha256", "review_sha256", "review_checks")}
    payload["scenario"] = scenario
    if scenario["scenario"] == "recovery":
        payload["recovery"] = replay["recovery"]
    if replay["mcp"]:
        payload["mcp"] = replay["mcp"]
    st.download_button("Download JSON evidence", data=json.dumps(payload, indent=2, allow_nan=False) + "\n",
                       file_name=f"strokeweaver-{scenario['scenario']}-evidence.json", mime="application/json")
    with st.expander("Evidence bindings"):
        for key, label in (("summary_sha256", "Run summary"), ("review_sha256", "Independent review")):
            st.caption(label)
            st.code(replay[key], language=None)
        for key, label in (("report_sha256", "Scenario report"), ("trace_sha256", "Execution trace"),
                           ("artifact_sha256", "Probability artifact"), ("task_binding", "Task binding")):
            st.caption(label)
            st.code(scenario[key], language=None)


def main():
    st.set_page_config(page_title="StrokeWeaver | Evidence Workbench", layout="wide")
    st.markdown(STYLE, unsafe_allow_html=True)
    st.markdown('<div class="sw-kicker">LOCAL RESEARCH WORKBENCH</div>', unsafe_allow_html=True)
    st.title("StrokeWeaver 2.0 · Evidence Workbench")
    st.caption("Audited replay on generated, nonpatient inputs.")
    try:
        replay = load_public_replay()
    except (EvidenceDenied, OSError) as error:
        st.warning("Replay locked until the independent evidence checks pass.")
        if isinstance(error, EvidenceDenied):
            st.caption(str(error))
        st.stop()

    with st.sidebar:
        st.header("Replay scenarios")
        name = st.radio("Scenario", tuple(TITLES), format_func=TITLES.__getitem__, label_visibility="collapsed")
        st.markdown("**Evidence receipt**")
        st.caption(replay["attempt"])
        st.caption(f"{replay['review_checks']} scenarios independently verified")
        st.markdown("**Data scope**")
        st.caption("Generated inputs · Protected labels sealed")
    scenario = replay["scenarios"][name]
    st.header(TITLES[name], anchor=False)
    status = "Verified technical completion" if scenario["terminal"] == "STOP" else "Referred for human review"
    st.caption(status + (f" · {scenario['reason']}" if scenario["reason"] else ""))
    cols = st.columns(4)
    for column, label, value in zip(cols,
                                    ("Terminal", "Elapsed", "Model tool calls", "Vision forwards"),
                                    (scenario["terminal"], f"{scenario['elapsed_seconds']:.2f} s",
                                     scenario["tool_calls"], scenario["vision_forwards"])):
        column.metric(label, value)
    if name == "recovery":
        st.info(f"Restart verified after SIGKILL (exit −9). The committed artifact was reused. "
                f"Restart wall time {replay['recovery']['restart_seconds']:.2f} s.")
    st.markdown('<div class="sw-divider"></div>', unsafe_allow_html=True)
    trace_tab, timing_tab, review_tab, mcp_tab, report_tab = st.tabs(
        ["Trace", "Timing", "Human review", "MCP", "Report"]
    )
    with trace_tab:
        display_timeline(scenario)
    with timing_tab:
        st.subheader("Recorded elapsed time")
        st.dataframe([{"Phase": PHASE_LABELS[key], "Seconds": round(value, 4)}
                      for key, value in scenario["phase_seconds"].items()], hide_index=True, width="stretch")
        st.caption(f"Local model requests in this scenario: {scenario['model_requests']}.")
    with review_tab:
        show_review(scenario)
    with mcp_tab:
        show_mcp(replay)
    with report_tab:
        show_export(replay, scenario)


main()
