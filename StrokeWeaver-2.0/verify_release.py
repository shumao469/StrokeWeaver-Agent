"""Verify the shipped replay and exercise a fresh local MCP subprocess."""

import json

from public_release import load_public_replay
from test_mcp_stdio import qualify


def main():
    replay = load_public_replay()
    checks = qualify((replay["attempt"], replay["summary_sha256"], replay["review_sha256"]))
    print(json.dumps({
        "attempt": replay["attempt"],
        "scenarios": {name: item["terminal"] for name, item in replay["scenarios"].items()},
        "mcp_checks_passed": sum(checks.values()),
        "mcp_checks_total": len(checks),
    }, indent=2))


if __name__ == "__main__":
    main()
