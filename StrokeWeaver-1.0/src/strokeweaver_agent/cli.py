"""Portable fixed-action CLI. Outputs only generated artifacts to stdout."""

import argparse
import json

from . import api, audit, nifti_guard, routing


def parser():
    result = argparse.ArgumentParser(prog="strokeweaver", description="StrokeWeaver Agent — generated-only research demo; no patient/model execution.")
    sub = result.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run actual generated native-space arithmetic and technical repair")
    demo.add_argument("--fixture", choices=(*api.FIXTURES, "all"), default="centimeter_encoded")
    demo.add_argument("--format", choices=("json", "html"), default="json")
    compare = sub.add_parser("compare", help="Compare five shared policies on declared dimensionless tasks")
    compare.add_argument("--scenario", choices=(*api.SCENARIOS, "all"), default="witness")
    compare.add_argument("--mode", choices=("retain", "mask", "uninformative"), default="retain")
    compare.add_argument("--fixed-observation", action="store_true", help="Hold an initial diagnostic observation and its sunk cost fixed")
    compare.add_argument("--format", choices=("json", "html"), default="json")
    guard = sub.add_parser("input-check", help="Validate fixed generated NIfTI bytes; never opens an input path")
    guard.add_argument("--case", choices=nifti_guard.CASES, default="canonical")
    guard.add_argument("--mode", choices=tuple(nifti_guard.MODE_MODALITIES), default="full_ensemble")
    guard.add_argument("--fault", choices=("none", *(r["name"] for r in nifti_guard.mutation_cases() if not r["expect_pass"])), default="none")
    guard.add_argument("--all-cases", action="store_true")
    guard.add_argument("--format", choices=("json", "html"), default="json")
    plan = sub.add_parser("plan", help="Preview only: deterministic generated-task intent routing, not an LLM")
    plan.add_argument("request")
    sub.add_parser("tools", help="Show generated tools and disabled external-model metadata")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "demo":
        report = api.run_batch() if args.fixture == "all" else api.run_demo(args.fixture)
    elif args.command == "compare":
        report = api.compare_policies(args.scenario, args.mode, args.fixed_observation)
    elif args.command == "input-check":
        report = api.check_all_inputs() if args.all_cases else api.check_generated_input(args.case, args.mode, args.fault)
    elif args.command == "plan":
        print(json.dumps(routing.preview(args.request), indent=2))
        return 0
    else:
        print(json.dumps(api.tool_registry(), indent=2))
        return 0
    print(audit.to_html(report) if args.format == "html" else audit.to_json(report))
    return 0
