"""Qualify the read-only adapter as a real stdio child, after independent PASS."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).absolute().parent
sys.path.insert(0, str(ROOT))
import mcp_stdio as server


def frame(request_id, method, params=None):
    value = {"jsonrpc": "2.0", "method": method}
    if request_id is not None:
        value["id"] = request_id
    if params is not None:
        value["params"] = params
    return server.encoded(value) + b"\n"


def child(pins, request_bytes=b""):
    env = {"CUDA_VISIBLE_DEVICES": ""}
    if os.name == "nt" and "SystemRoot" in os.environ:
        env["SystemRoot"] = os.environ["SystemRoot"]
    args = [sys.executable, "-I", "-S", "-B", str(ROOT / "mcp_stdio.py"),
            "--attempt", pins[0], "--summary-sha256", pins[1], "--audit-sha256", pins[2]]
    return subprocess.run(args, cwd=ROOT, env=env, input=request_bytes, capture_output=True, timeout=15, shell=False)


def qualify(pins):
    expect = server.project(*pins)
    init = {"protocolVersion": server.VERSION, "capabilities": {},
            "clientInfo": {"name": "generated-stdio-qualification", "version": "1"}}
    sequence = (
        frame(1, "tools/list") + frame(2, "initialize", init) + frame(3, "tools/list") +
        frame(None, "notifications/initialized") + frame(4, "tools/list") +
        frame(5, "tools/call", {"name": "get_task_status", "arguments": {}}) +
        frame(6, "tools/call", {"name": "get_technical_handoff", "arguments": {}}) +
        frame(7, "tools/call", {"name": "get_task_status", "arguments": {"path": "../not-admitted"}}) +
        frame(8, "tools/call", {"name": "launch", "arguments": {}}) +
        frame(9, "resources/read", {"uri": "file:///not-admitted"}) +
        frame(10, "tools/call", {"name": "get_technical_handoff", "arguments": []}) +
        frame(11, "ping") +
        b'{"jsonrpc":"2.0","method":"tools/list","method":"tools/call","id":12}\n'
    )
    process = child(pins, sequence)
    server.need(process.returncode == 0 and not process.stderr and len(process.stdout) <= 32_768)
    lines = [server.object_json(line) for line in process.stdout.splitlines()]
    server.need([row.get("id") for row in lines] == [*range(1, 12), None] and
                all(row.get("jsonrpc") == "2.0" for row in lines))
    rows = {row["id"]: row for row in lines}
    served = rows[4]["result"]["tools"]
    checks = {
        "stdio_subprocess_clean_exit_and_framing": True,
        "only_after_initialized_notification": rows[1]["error"]["code"] == rows[3]["error"]["code"] == -32600,
        "initialize_exact_protocol_and_tools_capability": rows[2]["result"]["protocolVersion"] == server.VERSION and
            rows[2]["result"]["capabilities"] == {"tools": {"listChanged": False}},
        "exact_two_readonly_tools": [x["name"] for x in served] == list(server.NAMES) and
            all(x["inputSchema"] == {"type": "object", "additionalProperties": False} and
                x["annotations"]["readOnlyHint"] is True for x in served),
        "generated_status_projection_matches_bound_artifacts": rows[5]["result"]["isError"] is False and
            rows[5]["result"]["structuredContent"] == expect["get_task_status"] and
            rows[5]["result"]["content"] == [{"type": "text", "text": server.encoded(expect["get_task_status"]).decode("ascii")}],
        "technical_handoff_projection_matches_bound_artifacts": rows[6]["result"]["isError"] is False and
            rows[6]["result"]["structuredContent"] == expect["get_technical_handoff"] and
            rows[6]["result"]["content"] == [{"type": "text", "text": server.encoded(expect["get_technical_handoff"]).decode("ascii")}],
        "caller_path_argument_denied_and_not_echoed": rows[7]["error"]["code"] == -32602 and
            b"not-admitted" not in process.stdout,
        "launch_tool_denied": rows[8]["error"]["code"] == -32602,
        "resource_file_method_denied": rows[9]["error"]["code"] == -32601,
        "wrong_argument_type_denied": rows[10]["error"]["code"] == -32602,
        "ping_works_without_extra_capability": rows[11].get("result") == {},
        "duplicate_json_key_denied": rows[None]["error"]["code"] == -32700,
        "no_raw_artifact_paths_or_content": all(word not in process.stdout for word in
            (b"task_binding", b"artifact_sha256", b"report.json", b"review.json", b"trace_sha256", b".nii")),
    }
    for label, invalid in (
        ("tampered_summary_pin_fails_startup", (pins[0], "0" * 64, pins[2])),
        ("tampered_audit_pin_fails_startup", (pins[0], pins[1], "0" * 64)),
        ("traversal_attempt_fails_startup", ("../qualification-v1", pins[1], pins[2])),
    ):
        denied = child(invalid, frame(1, "initialize", init))
        checks[label] = (denied.returncode == 2 and denied.stdout == b"" and
                         denied.stderr.strip() == b"Generated MCP audit gate closed")
    checks["generated_audit_and_projection_unchanged"] = server.project(*pins) == expect
    server.need(all(checks.values()))
    return checks


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--summary-sha256", required=True)
    parser.add_argument("--audit-sha256", required=True)
    a = parser.parse_args()
    pins = a.attempt, a.summary_sha256, a.audit_sha256
    try:
        checks = qualify(pins)
        path = ROOT / "runs" / a.attempt / "mcp_qualification.json"
        for parent in reversed(path.parents):
            server.need(parent.is_dir())
            server.no_redirect(parent)
        receipt = {"schema": "strokeweaver-generated-mcp-qualification-v1", "status": "PASS",
                   "scope": "generated_nonpatient", "attempt": a.attempt,
                   "summary_sha256": a.summary_sha256, "audit_sha256": a.audit_sha256,
                   "tools": list(server.NAMES), "transport": "stdio", "protocol_version": server.VERSION,
                   "checks": checks, "passed_checks": sum(checks.values()), "total_checks": len(checks),
                   "read_only_tools": True, "gpu_dispatched": False, "patient_execution": False,
                   "training": False, "formal_comparison": False, "protected_labels_sealed": True,
                   "source_sha256": {name: server.digest(server.read_bytes(ROOT / name))
                                     for name in ("mcp_stdio.py", "test_mcp_stdio.py")}}
        # Qualification writes only this new receipt. The server never writes.
        with path.open("xb") as stream:
            stream.write(server.encoded(receipt) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        print(server.encoded({"status": "PASS", "passed_checks": len(checks), "total_checks": len(checks)}).decode("ascii"))
        return 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError, subprocess.SubprocessError):
        print('{"status":"BLOCKED_OR_FAILED","reason":"MCP_QUALIFICATION_GATE_CLOSED"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
