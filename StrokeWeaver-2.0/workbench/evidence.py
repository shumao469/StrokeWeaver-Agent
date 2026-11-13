"""Read bounded, digest-bound non-patient evidence for the replay workbench."""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat


SCENARIOS = ("normal", "stale", "recovery")
ROOT = Path(__file__).resolve().parent.parent
PHASES = ("worker", "evidence", "llm", "report", "recovery", "other")
HASH = re.compile(r"[a-f0-9]{64}")
ATTEMPT = re.compile(r"qualification-v[1-9][0-9]{0,2}")
CODE = re.compile(r"[A-Za-z0-9_ .:+()-]{1,100}")
WINDOWS_REPARSE = 0x0400
SUMMARY_CAP = 131072
TRACE_CAP = 131072


class EvidenceDenied(ValueError):
    """A fixed message suitable for showing in the interface."""


def require(value, reason):
    if not value:
        raise EvidenceDenied(reason)


def no_duplicate_members(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON member")
        result[key] = value
    return result


def invalid_constant(_value):
    raise EvidenceDenied("Non-finite JSON value")


def read_json(raw):
    return json.loads(raw, object_pairs_hook=no_duplicate_members, parse_constant=invalid_constant)


def read_object(raw):
    value = read_json(raw)
    require(isinstance(value, dict), "Expected a JSON object")
    return value


def is_plain(path, kind):
    info = path.lstat()
    require(kind(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and not getattr(info, "st_file_attributes", 0) & WINDOWS_REPARSE,
            "Unexpected artifact path type")
    return info


def file_identity(info):
    # On Windows fstat may populate ctime from last-write rather than the
    # pathname's NTFS metadata-change timestamp for the very same handle.
    creation = getattr(info, "st_birthtime_ns", None) if os.name == "nt" else info.st_ctime_ns
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, creation


def read_locked(path, cap, expected=None):
    check = is_plain(path, stat.S_ISREG)
    require(check.st_nlink == 1 and 0 < check.st_size <= cap, "Artifact outside size or link bounds")
    if expected is not None:
        require(isinstance(expected, str) and HASH.fullmatch(expected), "Invalid digest in audit chain")
    with path.open("rb") as handle:
        require(file_identity(os.fstat(handle.fileno())) == file_identity(check), "Artifact identity changed")
        raw = handle.read(cap + 1)
        require(file_identity(os.fstat(handle.fileno())) == file_identity(check), "Artifact changed during read")
    require(len(raw) == check.st_size and file_identity(is_plain(path, stat.S_ISREG)) == file_identity(check),
            "Artifact changed after read")
    digest = hashlib.sha256(raw).hexdigest()
    require(expected is None or digest == expected, "Audit digest mismatch")
    return raw, digest


def short(value):
    return value if isinstance(value, str) and CODE.fullmatch(value) else None


def count(value, limit=10000):
    require(type(value) is int and 0 <= value <= limit, "Invalid execution count")
    return value


def seconds(value):
    require(type(value) in (int, float) and 0 <= value <= 86400 and math.isfinite(value),
            "Invalid elapsed time")
    return float(value)


def verified_checks(value):
    if isinstance(value, dict):
        states = list(value.values())
    elif isinstance(value, list):
        states = [row.get("pass", row.get("passed")) if isinstance(row, dict) else None for row in value]
    else:
        states = []
    require(states and len(states) <= 2000 and all(state is True for state in states),
            "Independent check records are incomplete")
    return len(states)


def public_trace(raw):
    rows = raw.splitlines()
    require(0 < len(rows) <= 120, "Unexpected scenario trace length")
    trace = []
    previous = "0" * 64
    prior_time = -1
    for position, row in enumerate(rows, start=1):
        event = read_object(row)
        name = short(event.get("event")) or short(event.get("kind")) or short(event.get("stage"))
        require(name is not None, "Trace event is missing its operation name")
        timestamp = event.get("monotonic_ns")
        require(type(event.get("seq")) is int and event["seq"] == position and
                event.get("previous_sha256") == previous and type(timestamp) is int and timestamp >= prior_time,
                "Trace event sequence changed")
        body = {key: value for key, value in event.items() if key != "sha256"}
        encoded = json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
        digest = hashlib.sha256(encoded.encode("ascii")).hexdigest()
        require(event.get("sha256") == digest, "Trace event digest changed")
        previous, prior_time = digest, timestamp
        safe = {"step": position, "event": name}
        detail = event.get("data", {})
        require(isinstance(detail, dict), "Invalid trace event data")
        for key in ("status", "reason", "terminal", "human_state", "action", "result", "before", "after",
                    "tool", "evidence_state", "state", "decision", "normalized_action"):
            value = short(detail.get(key))
            if value is not None:
                safe[key] = value
        for key in ("applicable", "artifact_reused", "valid"):
            if type(detail.get(key)) is bool:
                safe[key] = detail[key]
        for key in ("attempt", "tool_calls", "model_requests"):
            if type(detail.get(key)) is int:
                safe[key] = count(detail[key])
        if detail.get("returncode") == -9:
            safe["returncode"] = -9
        for key in ("elapsed_seconds", "wall_seconds", "phase_seconds", "restart_seconds"):
            value = detail.get(key)
            if type(value) in (int, float):
                safe[key] = seconds(value)
        trace.append(safe)
    return trace


def scenario_view(run, name, descriptor, audit):
    require(isinstance(descriptor, dict), "Scenario index record is invalid")
    folder = run / name
    is_plain(folder, stat.S_ISDIR)
    require(folder.resolve(strict=True) == folder, "Scenario directory changed")
    raw_report, report_sha = read_locked(folder / "report.json", SUMMARY_CAP, descriptor["report_sha256"])
    raw_trace, trace_sha = read_locked(folder / "events.jsonl", TRACE_CAP, descriptor["trace_sha256"])
    r = read_object(raw_report)
    expected_terminal = "REFER" if name == "stale" else "STOP"
    require(r["scenario"] == name and r["input_role"] == "generated_nonpatient" and
            r["terminal"] == descriptor["terminal"] == audit["terminal"] == expected_terminal and
            audit["trace_sha256"] == trace_sha and audit["artifact_sha256"] == r["artifact_sha256"] and
            audit["owned_forward_count"] == descriptor["launched_forward_count"] == 1 and
            audit["llm_requests"] == r["model_requests"] == (0 if name == "stale" else 2) and
            audit["recovered"] is (name == "recovery"),
            "Unexpected scenario role or terminal")
    expected_human = "PENDING_HUMAN" if r["terminal"] == "REFER" else "NOT_REQUIRED"
    require(r["human_state"] == audit["human_state"] == expected_human and
            isinstance(r["artifact_sha256"], str) and HASH.fullmatch(r["artifact_sha256"]),
            "Terminal and human review state disagree")
    require(isinstance(r["task_binding"], str) and HASH.fullmatch(r["task_binding"]),
            "Scenario task binding is invalid")
    phases = r["phase_seconds"]
    require(isinstance(phases, dict) and set(phases) == set(PHASES), "Scenario phase timing is incomplete")
    trace = public_trace(raw_trace)
    phases = {phase: seconds(phases[phase]) for phase in PHASES}
    elapsed = seconds(descriptor["total_seconds"])
    residual = elapsed - sum(phases.values())
    require(residual >= -0.020, "Audited phase timings exceed the host total")
    phases["host_residual"] = max(0.0, residual)
    require(trace[-1].get("event") == "TERMINAL" and trace[-1].get("terminal") == expected_terminal,
            "Trace lacks the audited terminal outcome")
    return {
        "scenario": name, "terminal": r["terminal"], "reason": short(r["reason"]),
        "human_state": r["human_state"], "artifact_sha256": r["artifact_sha256"], "task_binding": r["task_binding"],
        "tool_calls": count(r["tool_calls"]), "model_requests": count(r["model_requests"]),
        "vision_forwards": count(descriptor["launched_forward_count"]), "elapsed_seconds": elapsed,
        "phase_seconds": phases, "report_sha256": report_sha, "trace_sha256": trace_sha, "trace": trace,
    }


def read_mcp(run, summary_sha, review_sha):
    """Read only the separately bound MCP qualification receipt."""
    path = run / "mcp_qualification.json"
    if not path.exists():
        return None
    raw, digest = read_locked(path, SUMMARY_CAP)
    r = read_object(raw)
    if r.get("summary_sha256") != summary_sha or r.get("audit_sha256") != review_sha:
        return None
    require(r.get("schema") == "strokeweaver-generated-mcp-qualification-v1" and
            r.get("status") == "PASS" and r.get("transport") == "stdio" and
            r.get("attempt") == run.name and r.get("scope") == "generated_nonpatient" and
            r.get("read_only_tools") is True and r.get("protected_labels_sealed") is True and
            all(r.get(key) is False for key in ("patient_execution", "gpu_dispatched", "formal_comparison", "training")),
            "MCP qualification is invalid")
    version = short(r.get("protocol_version"))
    tools = r.get("tools")
    require(version is not None and tools == ["get_task_status", "get_technical_handoff"],
            "MCP qualification does not identify the expected tools")
    checks = verified_checks(r.get("checks"))
    require(checks == r.get("passed_checks") == r.get("total_checks"), "MCP check totals disagree")
    return {"transport": "stdio", "protocol_version": version, "tools": tools,
            "checks": checks, "receipt_sha256": digest}


def load_replay(attempt=None, *, root=ROOT, audit_sha256=None):
    attempt = attempt if attempt is not None else os.getenv("STROKEWEAVER_REPLAY_ATTEMPT", "")
    require(isinstance(attempt, str) and ATTEMPT.fullmatch(attempt) and attempt not in (".", ".."),
            "Set the audited run name to open its evidence")
    root = root.resolve(strict=True)
    audit_sha256 = audit_sha256 or os.getenv("STROKEWEAVER_REPLAY_AUDIT_SHA256", "")
    require(isinstance(audit_sha256, str) and HASH.fullmatch(audit_sha256),
            "Set the SHA-256 of the independent review receipt")
    runs = root / "runs"
    run = runs / attempt
    try:
        for directory in (runs, run):
            is_plain(directory, stat.S_ISDIR)
            require(directory.resolve(strict=True) == directory, "Replay directory changed")
        # Audit status is checked before any scenario data is read.
        raw_review, review_sha = read_locked(run / "independent_review.json", SUMMARY_CAP, audit_sha256)
        review = read_object(raw_review)
        require(review.get("status") == "PASS" and review.get("scope") == "generated_nonpatient" and
                review.get("patient_execution") is False and review.get("protected_labels_sealed") is True,
                "Independent review has not passed for the sealed generated scope")
        digest = review.get("summary_sha256")
        require(isinstance(digest, str) and HASH.fullmatch(digest), "Independent review is not bound to a summary")
        raw_summary, summary_sha = read_locked(run / "summary.json", SUMMARY_CAP, digest)
        s = read_object(raw_summary)
        require(s.get("scope") == "generated_nonpatient" and s.get("protected_labels_sealed") is True
                and all(s.get(key) is False for key in ("patient_execution", "formal_comparison", "training")),
                "Summary is outside the sealed generated scope")
        checks = review.get("checks")
        require(isinstance(checks, dict) and set(checks) == set(SCENARIOS) and
                all(isinstance(checks[name], dict) for name in SCENARIOS),
                "Independent scenario checks are incomplete")
        index = s["scenarios"]
        require(isinstance(index, dict) and set(index) == set(SCENARIOS), "Expected all three audited scenarios")
        scenarios = {name: scenario_view(run, name, index[name], checks[name]) for name in SCENARIOS}
        recovery = s["recovery"]
        require(recovery.get("kill_returncode") == -9 and recovery.get("artifact_reused") is True,
                "Recovery proof is absent")
        read_locked(run / "independent_review.json", SUMMARY_CAP, review_sha)
        return {
            "attempt": attempt, "scope": s["scope"], "summary_sha256": summary_sha, "review_sha256": review_sha,
            "review_checks": len(checks), "scenarios": scenarios,
            "recovery": {"kill_returncode": -9, "artifact_reused": True,
                         "restart_seconds": seconds(recovery["restart_seconds"])},
            "mcp": read_mcp(run, summary_sha, review_sha),
        }
    except EvidenceDenied:
        raise
    except (KeyError, AttributeError, TypeError, UnicodeError, ValueError, OSError) as error:
        raise EvidenceDenied("Audited run receipts are missing or invalid") from error
