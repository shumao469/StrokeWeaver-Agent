"""Local synthetic chat and timing workbench for StrokeWeaver."""

from collections import Counter
from dataclasses import dataclass, field
import json
from math import isfinite
from pathlib import Path
import sys
from time import monotonic
from uuid import uuid4

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sw3_phase2.core import Episode, KINDS, digest, load_demo_cases
from sw3_phase2.followup.chat import LocalModel, ModelUnavailable
from sw3_phase2.followup.release.scope import WorkbenchNavigationPolicy


_ARMS = {
    "strokeweaver": "Evidence-aware chat",
    "retrieval_chat": "Retrieval chat",
    "checklist": "Fixed checklist",
}
_ISSUES = {
    "MISSING": "Missing record",
    "CONFLICT": "Conflicting sources",
    "HANDOFF_PENDING": "Handoff awaiting confirmation",
}
_STATUSES = {
    "DRAFT": ("Awaiting signature", "blue"),
    "NEEDS_REVIEW": ("Review required", "orange"),
    "SIGNED": ("Signed", "green"),
    "STALE": ("Signature expired", "orange"),
}
_ACTIONS = {
    "ANSWER": "Record found",
    "CLARIFY": "Clarification required",
    "REVIEW": "Review required",
    "REFER": "Referred for review",
}
_OUTCOMES = {"ready": "Review complete", "review_needed": "Review items remain", "stopped": "Stopped early"}


def _kind(kind):
    return {"imaging": "Imaging report", "medications": "Medication record", "rehab": "Rehabilitation", "follow_up": "Follow-up"}.get(kind, "Handoff")


def _time_label(stamp):
    return stamp.replace("T", " ").replace("Z", " UTC")


@dataclass
class TimingTrial:
    case_id: str
    arm: str
    initial_sha256: str
    id: str = field(default_factory=lambda: uuid4().hex)
    started_at: float = field(default_factory=monotonic)
    interactions: Counter = field(default_factory=Counter)
    reply_actions: Counter = field(default_factory=Counter)
    model_calls: int = 0
    tool_calls: int = 0
    recovery_attempts: int = 0
    failures: int = 0
    model_wall_seconds: float = 0.0

    def record_chat(self, reply):
        self.interactions["chat_submitted"] += 1
        action = reply.get("action")
        self.reply_actions[action if action in _ACTIONS else "OTHER"] += 1
        for key in ("model_calls", "tool_calls", "recovery_attempts", "model_wall_seconds"):
            value = reply.get(key, 0)
            if type(value) in (int, float) and isfinite(value) and value >= 0:
                setattr(self, key, getattr(self, key) + value)
        if reply.get("failure"):
            self.failures += 1

    def mark_correction(self):
        self.interactions["participant_marked_correction"] += 1

    def finish(self, policy, participant_outcome):
        elapsed_seconds = round(monotonic() - self.started_at, 3)
        state = policy.state()
        receipt = {
            "schema": "strokeweaver-synthetic-timing-rehearsal-v1",
            "generated_only": True,
            "pilot_rehearsal_only": True,
            "run_id": self.id,
            "case_id": self.case_id,
            "arm": self.arm,
            "elapsed_seconds": elapsed_seconds,
            "participant_outcome": participant_outcome,
            "initial_snapshot_sha256": self.initial_sha256,
            "final_snapshot_sha256": state["snapshot_sha256"],
            "final_plan_status": state["plan_status"],
            "pending_issues": len(state["issues"]),
            "pending_referrals": sum(row["status"] == "PENDING" for row in state["referrals"]),
            "interactions": dict(self.interactions),
            "reply_actions": dict(self.reply_actions),
            "model_calls": self.model_calls,
            "tool_calls": self.tool_calls,
            "recovery_attempts": self.recovery_attempts,
            "model_failures": self.failures,
            "model_wall_seconds": round(self.model_wall_seconds, 6),
        }
        return {**receipt, "receipt_sha256": digest(receipt)}


@dataclass
class Conversation:
    policy: object
    turns: dict = field(default_factory=lambda: {"doctor": [], "patient": []})
    patient_binding: tuple = ()
    source_id: str | None = None
    notice: str | None = None

    def choose_source(self, record_id, trial):
        self.source_id = record_id
        if trial:
            trial.interactions["source_opened"] += 1

    def run_review_action(self, name, args, trial):
        if trial:
            trial.interactions[name + "_attempted"] += 1
        try:
            getattr(self.policy, name)(*args)
        except ValueError as error:
            self.notice = str(error)
            return
        if trial:
            trial.interactions[name + "_succeeded"] += 1


def _new_conversation(arm, case, model):
    policy = Episode(case) if arm == "checklist" else WorkbenchNavigationPolicy(arm, case, model)
    return Conversation(policy)


def _show_status(status):
    label, color = _STATUSES[status]
    st.badge(label, color=color)


def _model_controls(model):
    with st.expander("Local model connection"):
        if st.button("Verify loaded model", key="followup_model_identity"):
            try:
                st.session_state.followup_identity = model.identity()
                st.session_state.followup_identity_failed = False
            except ModelUnavailable:
                st.session_state.pop("followup_identity", None)
                st.session_state.followup_identity_failed = True
        if "followup_identity" in st.session_state:
            st.success("Local model identity verified")
            st.json(st.session_state.followup_identity, expanded=False)
        if st.session_state.get("followup_identity_failed"):
            st.warning("Local model unavailable. The response uses the controlled fallback and records the status.")


def _submit_chat(conversation, role, trial, message):
    snapshot = conversation.policy.state()["snapshot_sha256"] if role == "doctor" else None
    with st.spinner("Checking current records…", show_time=True):
        reply = conversation.policy.chat(role, message)
    if trial:
        trial.record_chat(reply)
    turns = conversation.turns[role]
    turns.append((message, reply, snapshot))
    if len(turns) > 8:
        del turns[:-8]


def _doctor_reply(conversation, reply, source_ids, row, trial, key):
    if reply["action"] in _ACTIONS:
        st.caption(_ACTIONS[reply["action"]])
    if reply.get("failure"):
        st.caption("Local model fallback")
    valid_citations = list(dict.fromkeys(source_id for source_id in reply["citations"] if source_id in source_ids))
    for item, source_id in enumerate(valid_citations):
        st.button(
            f"View source · {source_id}",
            key=f"{key}_citation_{row}_{item}",
            on_click=conversation.choose_source,
            args=(source_id, trial),
        )


def _queue_chat(key):
    question = st.session_state.get(key, "").strip()
    if question:
        st.session_state.followup_chat_request = (key, question)


def _chat(conversation, role, scope, *, state, trial=None):
    if role == "patient":
        plan = state["plan"]
        binding = (state["plan_status"], plan["plan_id"]) if plan else (state["plan_status"],)
        if binding != conversation.patient_binding:
            conversation.turns["patient"].clear()
            conversation.patient_binding = binding
    turns = conversation.turns[role]
    if not turns:
        st.caption("For example: summary. Follow up with: source?" if role == "doctor"
                   else "For example: show my signed plan.")
    source_ids = {record["id"] for record in state["timeline"]} if role == "doctor" else set()
    with st.container(height=385, border=True, autoscroll=True):
        if not turns:
            with st.chat_message("assistant"):
                st.write("Review the imaging, medication, rehabilitation or follow-up records." if role == "doctor"
                         else "I can show the simulated clinician-signed discharge plan.")
        for row, (question, reply, snapshot) in enumerate(turns):
            with st.chat_message("user"):
                st.text(question)
            with st.chat_message("assistant"):
                if role == "doctor" and snapshot != state["snapshot_sha256"]:
                    st.badge("Earlier snapshot", color="gray")
                st.text(reply["text"])
                if role == "doctor":
                    _doctor_reply(conversation, reply, source_ids, row, trial, scope)
    key = f"{scope}_{role}_chat"
    st.chat_input("Ask about this synthetic case", key=key, max_chars=500, on_submit=_queue_chat, args=(key,))


def _source_panel(conversation, state, scope, trial):
    st.markdown("##### Source records")
    records = {row["id"]: row for row in state["timeline"]}
    if not records:
        st.caption("No records are available.")
        return
    newest = sorted(records.values(), key=lambda row: (row["recorded_at"], row["id"]), reverse=True)
    with st.popover("Browse case timeline"):
        for record in newest:
            st.button(
                f"{_kind(record['kind'])} · v{record['version']} · {record['id']}",
                key=f"{scope}_source_{record['id']}",
                on_click=conversation.choose_source,
                args=(record["id"], trial),
            )
    current_source = records.get(conversation.source_id)
    if current_source:
        active = {row["id"] for row in state["current"]}
        with st.container(border=True):
            st.markdown(f"**{_kind(current_source['kind'])}**")
            st.badge("Current evidence" if current_source["id"] in active else "Outside current plan",
                     color="green" if current_source["id"] in active else "gray")
            st.caption(f"{current_source['id']} · v{current_source['version']} · "
                       f"{_time_label(current_source['recorded_at'])}")
            st.text(current_source["text"])
            if current_source["supersedes"]:
                st.caption(f"Supersedes {current_source['supersedes']}")
    else:
        st.caption("Open a record from a citation or the timeline.")


def _review_button(conversation, label, name, args, scope, trial, *, disabled=False, primary=False, suffix=""):
    st.button(
        label,
        key=f"{scope}_{name}_{suffix}",
        disabled=disabled,
        type="primary" if primary else "secondary",
        on_click=conversation.run_review_action,
        args=(name, args, trial),
    )


def _review(conversation, state, scope, trial):
    st.markdown("##### Review and sign")
    if conversation.notice:
        st.warning(conversation.notice)
        conversation.notice = None
    snapshot = state["snapshot_sha256"]
    for issue in state["issues"]:
        kind, code = issue["kind"], issue["code"]
        st.caption(f"{_ISSUES[code]} · {_kind(kind)}")
        if code == "CONFLICT":
            choice = st.selectbox(
                "Select the source to use", issue["record_ids"], index=None,
                key=f"{scope}_conflict_{issue['id']}", placeholder="Choose after reviewing the sources",
            )
            _review_button(conversation, "Confirm source", "resolve_conflict", (kind, choice, snapshot),
                           scope, trial, disabled=choice is None, suffix=issue["id"])
        elif code == "HANDOFF_PENDING":
            _review_button(conversation, "Confirm handoff", "acknowledge_handoff", (), scope, trial)
    if state["plan_status"] != "SIGNED":
        _review_button(conversation, "Sign current plan", "approve", (snapshot,), scope, trial,
                       disabled=bool(state["issues"]), primary=True)
    if conversation.policy.can_update:
        _review_button(conversation, "Receive simulated update", "apply_update", (), scope, trial)
    for row in state["referrals"]:
        st.text(row["message"])
        if row["status"] == "PENDING":
            _review_button(conversation, "Acknowledge referral", "acknowledge_referral", (row["id"],), scope, trial,
                           suffix=row["id"])
    if trial:
        st.button(
            "Record a manual correction", on_click=trial.mark_correction, key=f"{scope}_mark_correction",
            help="Record each correction after it occurs. Only the count is included in the receipt.",
        )


def _checklist(conversation, state, scope, trial):
    st.subheader("Fixed handoff checklist")
    current = {row["kind"]: row for row in state["current"]}
    for kind in KINDS:
        row = current.get(kind)
        with st.container(border=True):
            st.markdown(f"**{_kind(kind)}**")
            if row:
                st.text(row["text"])
                st.button(
                    f"View source · {row['id']}",
                    key=f"{scope}_checklist_{row['id']}",
                    on_click=conversation.choose_source,
                    args=(row["id"], trial),
                )
            else:
                st.caption("Review needed")


def _workbench(conversation, arm, role, scope, trial=None):
    policy = conversation.policy
    pending = st.session_state.pop("followup_chat_request", None)
    if pending and pending[0] == f"{scope}_{role}_chat" and arm != "checklist":
        _submit_chat(conversation, role, trial, pending[1])
    if role == "patient":
        state = policy.patient_state()
        st.subheader("Discharge plan and questions")
        _show_status(state["plan_status"])
        plan = state["plan"]
        if plan:
            with st.expander("View signed plan"):
                for section in plan["sections"]:
                    st.markdown(f"**{_kind(section['kind'])}**")
                    st.text(section["text"])
        else:
            st.caption("The plan is awaiting clinician confirmation.")
        _chat(conversation, role, scope, state=state)
        return
    state = policy.state()
    st.caption(f"{policy.case_id} · {_time_label(policy.as_of)}")
    _show_status(state["plan_status"])
    left, right = st.columns([2, 1], gap="large")
    with left:
        if arm == "checklist":
            _checklist(conversation, state, scope, trial)
        else:
            st.subheader("Handoff chat")
            _chat(conversation, role, scope, state=state, trial=trial)
    with right:
        _source_panel(conversation, state, scope, trial)
        st.divider()
        _review(conversation, state, scope, trial)


def _case_selector(fixtures, key, doctor=True, *, disabled=False):
    return st.selectbox(
        "Synthetic case", list(fixtures), key=key, disabled=disabled,
        format_func=(lambda case_id: fixtures[case_id]["title"]) if doctor else str,
    )


def _demo(fixtures, model):
    with st.sidebar:
        arm = st.radio("Workflow", list(_ARMS), format_func=_ARMS.get, key="followup_demo_arm")
        role = "doctor"
        if arm != "checklist":
            role = st.radio(
                "Demo role", ("doctor", "patient"), key="followup_role",
                format_func={"doctor": "Clinician", "patient": "Patient / caregiver"}.get,
            )
        case_id = _case_selector(fixtures, "followup_demo_case", role == "doctor")
        if role == "doctor" and arm != "checklist":
            _model_controls(model)
    conversations = st.session_state.setdefault("followup_demo_conversations", {})
    if (arm, case_id) not in conversations:
        conversations[arm, case_id] = _new_conversation(arm, fixtures[case_id], model)
    _workbench(conversations[arm, case_id], arm, role, f"demo_{arm}_{case_id}")


@st.fragment(run_every=1)
def _timer(trial):
    st.caption(f"Timer running · {monotonic() - trial.started_at:.0f} s")


def _start_trial(arm, case, model):
    if st.session_state.get("followup_active_trial"):
        return
    conversation = _new_conversation(arm, case, model)
    trial = TimingTrial(case["case_id"], arm, conversation.policy.state()["snapshot_sha256"])
    st.session_state.followup_active_trial = (trial, conversation)
    st.session_state.pop("followup_trial_receipt", None)


def _finish_trial(expected_id, outcome_key):
    active = st.session_state.get("followup_active_trial")
    outcome = st.session_state.get(outcome_key)
    if active and active[0].id == expected_id and outcome in _OUTCOMES:
        trial, conversation = active
        st.session_state.followup_trial_receipt = trial.finish(conversation.policy, outcome)
        st.session_state.pop("followup_active_trial")


def _study(fixtures, model):
    st.caption("Synthetic rehearsal timer. The receipt contains interaction counts, elapsed time and snapshot hashes.")
    active = st.session_state.get("followup_active_trial")
    with st.sidebar:
        arm = st.radio("Comparison workflow", list(_ARMS), format_func=_ARMS.get,
                       key="followup_study_arm", disabled=active is not None)
        case_id = _case_selector(fixtures, "followup_study_case", disabled=active is not None)
    if active is None:
        st.info("Select a synthetic case and begin. Review the handoff, then sign or leave items for review.")
        st.button(
            "Start rehearsal", type="primary", key="followup_start_trial",
            on_click=_start_trial, args=(arm, fixtures[case_id], model),
        )
        receipt = st.session_state.get("followup_trial_receipt")
        if receipt:
            st.success(f"Rehearsal complete · {receipt['elapsed_seconds']:.2f} s")
            st.download_button(
                "Download timing receipt",
                json.dumps(receipt, ensure_ascii=False, indent=2),
                f"{receipt['case_id']}-timing-rehearsal.json",
                mime="application/json",
            )
            st.json(receipt, expanded=False)
        return
    trial, conversation = active
    with st.sidebar:
        _timer(trial)
        outcome_key = f"followup_outcome_{trial.id}"
        outcome = st.selectbox(
            "Outcome",
            list(_OUTCOMES),
            index=None,
            format_func=_OUTCOMES.get,
            key=outcome_key,
        )
        st.button(
            "Finish and generate receipt", key="followup_finish_trial", disabled=outcome is None,
            on_click=_finish_trial, args=(trial.id, outcome_key),
        )
    _workbench(conversation, trial.arm, "doctor", f"trial_{trial.id}", trial)


def main(model=None):
    st.set_page_config(
        page_title="StrokeWeaver Handoff chat",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.html("""
        <style>
        [data-testid="stText"] pre { white-space: pre-wrap; overflow-wrap: anywhere; }
        </style>
    """)
    st.title("StrokeWeaver Handoff chat")
    st.caption("Local synthetic cases · Review sources, track updates and confirm handoffs")
    with st.sidebar:
        active = bool(st.session_state.get("followup_active_trial"))
        mode = st.radio(
            "Mode", ("demo", "study"), key="followup_mode", disabled=active,
            format_func={"demo": "Case chat", "study": "Synthetic research rehearsal"}.get,
        )
        if active:
            st.caption("Rehearsal in progress")
            mode = "study"
    fixtures = {case["case_id"]: case for case in load_demo_cases()}
    if model is None:
        model = LocalModel.from_env()
    if mode == "demo":
        _demo(fixtures, model)
    else:
        _study(fixtures, model)


if __name__ == "__main__":
    main()
