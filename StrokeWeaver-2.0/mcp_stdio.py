"""Pinned, generated-only MCP 2025-11-25 stdio tool server; never runs a task."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).absolute().parent
VERSION = "2025-11-25"
ATTEMPT = re.compile(r"qualification-v[1-9][0-9]{0,2}")
SHA = re.compile(r"[0-9a-f]{64}")
SCENARIOS = ("normal", "stale", "recovery")
EXPECTED = {"normal": ("STOP", "VERIFIED_STATUS_AND_ARTIFACT", "NOT_REQUIRED"),
            "stale": ("REFER", "STALE_EVIDENCE_CONTEXT", "PENDING_HUMAN"),
            "recovery": ("STOP", "VERIFIED_STATUS_AND_ARTIFACT", "NOT_REQUIRED")}
NAMES = ("get_task_status", "get_technical_handoff")
TOOLS = [
    {"name": name, "description": description,
     "inputSchema": {"type": "object", "additionalProperties": False},
     "annotations": {"readOnlyHint": True, "destructiveHint": False,
                     "idempotentHint": True, "openWorldHint": False}}
    for name, description in zip(NAMES, (
        "Read only the independently reviewed generated qualification outcome.",
        "Read only the technical handoff status for the generated stale-evidence case."
    ))
]
FILE_LIMIT = 524_288
LINE_LIMIT = 16_384
MESSAGE_LIMIT = 128


class Closed(ValueError):
    pass


def need(ok):
    if not ok:
        raise Closed("GENERATED_AUDIT_GATE_CLOSED")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def is_sha(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def no_redirect(path):
    info = path.lstat()
    need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400)
    return info


def read_bytes(path, cap=FILE_LIMIT):
    need(path.is_absolute() and ".." not in path.parts and ROOT in path.parents)
    for parent in reversed(path.parents):
        need(stat.S_ISDIR(no_redirect(parent).st_mode))
    before = no_redirect(path)
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= cap)
    # Windows lstat and fstat can report different ctime conventions for the
    # same NTFS file; device, file ID, length, mtime and link count still bind it.
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink")
    if os.name != "nt":
        fields += ("st_ctime_ns",)
    signature = tuple(getattr(before, k) for k in fields)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "rb") as fh:
        at_open = os.fstat(fh.fileno())
        need(stat.S_ISREG(at_open.st_mode) and tuple(getattr(at_open, k) for k in fields) == signature)
        data = fh.read(cap + 1)
        after = os.fstat(fh.fileno())
    now = no_redirect(path)
    need(len(data) == before.st_size and all(tuple(getattr(item, k) for k in fields) == signature
                                              for item in (after, now)))
    return data


def unique(pairs):
    result = {}
    for k, v in pairs:
        need(k not in result)
        result[k] = v
    return result


def bad_number(_):
    raise Closed("NONFINITE_JSON")


def object_json(raw):
    obj = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=bad_number)
    need(type(obj) is dict)
    return obj


def read_pinned(path, expected):
    need(is_sha(expected))
    raw = read_bytes(path)
    need(digest(raw) == expected)
    return object_json(raw)


def elapsed(value):
    need(type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 600)
    return value


def count(value, maximum):
    need(type(value) is int and 0 <= value <= maximum)
    return value


def project(attempt, summary_pin, audit_pin):
    """Return only allowlisted scalars; never return input records or paths."""
    need(type(attempt) is str and ATTEMPT.fullmatch(attempt) is not None)
    run = ROOT / "runs" / attempt
    summary = read_pinned(run / "summary.json", summary_pin)
    audit = read_pinned(run / "independent_review.json", audit_pin)
    need(audit.get("status") == "PASS" and audit.get("summary_sha256") == summary_pin and
         audit.get("protocol_sha256") == summary.get("protocol_sha256") and
         audit.get("scope") == "generated_nonpatient" and audit.get("patient_execution") is False and
         audit.get("protected_labels_sealed") is True and type(audit.get("checks")) is dict and
         set(audit["checks"]) == set(SCENARIOS))
    need(summary.get("schema") == "strokeweaver-generated-closed-loop-summary-v1" and
         summary.get("scope") == "generated_nonpatient" and summary.get("protected_labels_sealed") is True and
         all(summary.get(key) is False for key in ("patient_execution", "formal_comparison", "training")))
    protocol = read_pinned(ROOT / "protocol.json", summary.get("protocol_sha256"))
    need(protocol.get("schema") == "strokeweaver-generated-closed-loop-protocol-v1" and
         protocol.get("scope") == "generated_nonpatient" and protocol.get("protected_labels_sealed") is True and
         all(protocol.get(key) is False for key in ("patient_execution", "formal_comparison", "training")))
    need(type(summary.get("scenarios")) is dict and set(summary["scenarios"]) == set(SCENARIOS))
    projected = {}
    for name in SCENARIOS:
        row = summary["scenarios"][name]
        terminal, reason, human = EXPECTED[name]
        need(type(row) is dict and row.get("terminal") == terminal and is_sha(row.get("trace_sha256")))
        report = read_pinned(run / name / "report.json", row.get("report_sha256"))
        need(report.get("schema") == "strokeweaver-generated-closed-loop-report-v1" and
             report.get("scenario") == name and report.get("terminal") == terminal and
             report.get("reason") == reason and report.get("human_state") == human and
             report.get("input_role") == "generated_nonpatient" and
             report.get("protected_labels_sealed") is True and
             all(report.get(key) is False for key in ("patient_execution", "formal_comparison", "training")))
        checked = audit["checks"][name]
        need(type(checked) is dict and checked.get("terminal") == terminal and checked.get("human_state") == human and
             checked.get("trace_sha256") == row["trace_sha256"] and
             is_sha(checked.get("artifact_sha256")) and checked["artifact_sha256"] == report.get("artifact_sha256") and
             count(checked.get("owned_forward_count"), 1) == 1 and
             checked.get("recovered") is (name == "recovery"))
        projected[name] = {"terminal": terminal, "reason": reason, "human_state": human,
                           "tool_calls": count(report.get("tool_calls"), 3),
                           "model_requests": count(report.get("model_requests"), 2),
                           "launched_forward_count": count(row.get("launched_forward_count"), 1),
                           "total_seconds": elapsed(row.get("total_seconds"))}
        expected_calls, expected_requests = (0, 0) if name == "stale" else (1, 2)
        need(projected[name]["tool_calls"] == expected_calls and
             projected[name]["model_requests"] == count(checked.get("llm_requests"), 2) == expected_requests and
             projected[name]["launched_forward_count"] == 1)
    review = read_pinned(run / "stale" / "review.json", summary["scenarios"]["stale"].get("review_sha256"))
    need(review.get("scenario") == "stale" and review.get("state") == "PENDING_HUMAN" and
         review.get("reason") == "STALE_EVIDENCE_CONTEXT" and "operator_action" in review and
         review["operator_action"] is None and review.get("artifact_sha256") == audit["checks"]["stale"]["artifact_sha256"])
    recovery = summary.get("recovery")
    need(type(recovery) is dict and recovery.get("artifact_reused") is True and
         type(recovery.get("kill_returncode")) is int and recovery["kill_returncode"] in (-9, 137))
    scope = {"scope": "generated_nonpatient", "patient_execution": False, "formal_comparison": False,
             "training": False, "protected_labels_sealed": True}
    status = {**scope, "independent_review_status": "PASS", "scenarios": projected,
              "recovery": {"artifact_reused": True, "restart_seconds": elapsed(recovery.get("restart_seconds"))}}
    handoff = {**scope, "scenario": "stale", "state": "PENDING_HUMAN", "reason": "STALE_EVIDENCE_CONTEXT",
               "operator_action": None}
    return {NAMES[0]: status, NAMES[1]: handoff}


def encoded(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def respond(request_id, *, result=None, error=None):
    message = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        message["error"] = {"code": error[0], "message": error[1]}
    else:
        message["result"] = result
    sys.stdout.buffer.write(encoded(message) + b"\n")
    sys.stdout.buffer.flush()


def serve(pins):
    phase = 0
    seen = set()
    for _ in range(MESSAGE_LIMIT):
        line = sys.stdin.buffer.readline(LINE_LIMIT + 1)
        if not line:
            return 0
        if len(line) > LINE_LIMIT or not line.endswith(b"\n"):
            respond(None, error=(-32700, "Invalid frame"))
            return 2
        try:
            msg = object_json(line)
        except (ValueError, UnicodeError, RecursionError):
            respond(None, error=(-32700, "Invalid JSON object"))
            continue
        method = msg.get("method")
        if msg.get("jsonrpc") != "2.0" or type(method) is not str or len(method) > 100:
            respond(None, error=(-32600, "Invalid request"))
            continue
        if "id" not in msg:
            if method == "notifications/initialized" and phase == 1 and msg.get("params", {}) == {}:
                phase = 2
            continue
        request_id = msg["id"]
        if ((type(request_id) is not int or not -(2**53) < request_id < 2**53) and
                (type(request_id) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}", request_id))):
            respond(None, error=(-32600, "Invalid request ID"))
            continue
        if request_id in seen:
            respond(request_id, error=(-32600, "Duplicate request ID"))
            continue
        seen.add(request_id)
        params = msg.get("params", {})
        if type(params) is not dict:
            respond(request_id, error=(-32602, "Invalid parameters"))
            continue
        if method == "ping" and set(params) <= {"_meta"}:
            respond(request_id, result={})
        elif method == "initialize" and phase == 0:
            if (type(params.get("protocolVersion")) is not str or
                    type(params.get("clientInfo")) is not dict or
                    type(params.get("capabilities")) is not dict):
                respond(request_id, error=(-32602, "Invalid initialization parameters"))
                continue
            phase = 1
            respond(request_id, result={"protocolVersion": VERSION, "capabilities": {"tools": {"listChanged": False}},
                                         "serverInfo": {"name": "strokeweaver-generated-readback", "version": "1.0.0"}})
        elif phase != 2:
            respond(request_id, error=(-32600, "MCP initialization required"))
        elif method == "tools/list" and set(params) <= {"_meta"}:
            respond(request_id, result={"tools": TOOLS})
        elif method == "tools/call":
            name = params.get("name")
            if name not in NAMES:
                respond(request_id, error=(-32602, "Tool not allowed"))
            elif set(params) - {"name", "arguments", "_meta"} or type(params.get("arguments", {})) is not dict or params.get("arguments", {}):
                respond(request_id, error=(-32602, "This tool accepts no arguments"))
            else:
                try:
                    result = project(*pins)[name]
                except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
                    respond(request_id, result={"content": [{"type": "text", "text": "Generated audit gate closed"}],
                                                 "isError": True})
                    continue
                respond(request_id, result={"content": [{"type": "text", "text": encoded(result).decode("ascii")}],
                                             "structuredContent": result, "isError": False})
        else:
            respond(request_id, error=(-32601, "Method not allowed"))
    return 0


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise Closed("CLI_ARGUMENTS_REJECTED")


def main():
    p = Parser(allow_abbrev=False, add_help=False)
    p.add_argument("--attempt", required=True)
    p.add_argument("--summary-sha256", required=True)
    p.add_argument("--audit-sha256", required=True)
    try:
        a = p.parse_args()
        pins = a.attempt, a.summary_sha256, a.audit_sha256
        project(*pins)
        return serve(pins)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        print("Generated MCP audit gate closed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
