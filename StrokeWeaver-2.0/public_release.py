"""Fixed trust root for the byte-preserved generated replay release."""

from pathlib import Path

from workbench.evidence import EvidenceDenied, load_replay, read_locked, read_object


ROOT = Path(__file__).resolve().parent
ATTEMPT = "qualification-v1"
MANIFEST_SHA256 = "44de65cbe8b61091d17edc678ea9f9450a2f230648a6264a1d03ea7e50373e37"
RUN = f"runs/{ATTEMPT}"


def load_public_replay():
    manifest, _ = read_locked(ROOT / "evidence_manifest.json", 8192, MANIFEST_SHA256)
    pins = read_object(manifest)["files"]
    for relative, pin in pins.items():
        path = ROOT / relative
        if path.resolve(strict=True) != path:
            raise EvidenceDenied("Unexpected published evidence path")
        payload, _ = read_locked(path, 131_072, pin["sha256"])
        if len(payload) != pin["bytes"]:
            raise EvidenceDenied("Published evidence size disagrees with manifest")

    replay = load_replay(ATTEMPT, root=ROOT, audit_sha256=pins[f"{RUN}/independent_review.json"]["sha256"])
    if replay["mcp"] is None or replay["mcp"]["receipt_sha256"] != pins[f"{RUN}/mcp_qualification.json"]["sha256"]:
        raise EvidenceDenied("Published MCP receipt is missing or invalid")
    return replay
