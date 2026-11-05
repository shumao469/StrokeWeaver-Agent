"""Bounded generated task APIs. No patient/file/model execution interface."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from . import BRAND, INTERNAL_CONTROLLER, __version__
from . import controller as core
from . import nifti_guard

SCENARIOS = {"witness": 0, "redundant": 1, "unresolvable": 2}
ARM_LABELS = {
    "dependency_aware_deterministic": "Dependency-aware deterministic workflow",
    "strong_one_step_gate": "Strong rolling one-step gate",
    "strong_two_step_cascade": "Strong two-step cascade",
    "finite_complete_VOI": "Complete finite VOI",
    "applicability_aware_controller": "TACTIC (internal controller)",
}
FIXTURES = tuple(f["name"] for f in core.spatial_fixtures())
BOUNDARIES = {
    "generated_only": True, "patient_execution": False, "training_enabled": False,
    "protected_labels_used": False, "model_weights_bundled": False,
    "neural_inference_performed": False, "clinical_ready": False,
    "new_independent_validation": False,
}


def source_bindings():
    """Hash this package's own code only; never inspect a private workspace."""
    root = Path(__file__).resolve().parent
    names = ("controller.py", "nifti_guard.py", "api.py", "audit.py", "routing.py", "tool_registry.json")
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}


def _wrap(task, payload, started):
    report = {
        "schema": "strokeweaver-generated-research-audit-v1", "system": BRAND,
        "internal_controller": INTERNAL_CONTROLLER, "version": __version__, "task": task,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": BOUNDARIES.copy(), "payload": core.json_safe(payload),
        "source_bindings": source_bindings(),
        "cost": {"actual_api_wall_seconds": time.perf_counter() - started,
                 "scope": "Python task plus package provenance hashing; excludes CLI/UI startup, rendering, export and deployment. No neural/clinical speed claim."},
    }
    report["audit_sha256"] = core.digest(report)
    return report


def verify_audit(report):
    if type(report) is not dict or "audit_sha256" not in report:
        return False
    value = {key: item for key, item in report.items() if key != "audit_sha256"}
    try:
        return core.digest(value) == report["audit_sha256"]
    except (ValueError, TypeError):
        return False


def run_demo(fixture="centimeter_encoded"):
    if fixture not in FIXTURES:
        raise ValueError("Only registered self-generated fixtures are accepted")
    started = time.perf_counter()
    selected = next(f for f in core.spatial_fixtures() if f["name"] == fixture)
    workflow = core.run_spatial_workflow(selected)
    return _wrap("generated_native_space_workflow", {
        "workflow": workflow,
        "generated_data": {"input": selected["input"], "technical_reference": selected["technical_reference"],
                           "input_sha256": core.digest(selected["input"]),
                           "reference_role": "Self-generated spatial/arithmetic reference, not lesion ground truth"},
        "interpretation": "STOP requires a passed technical recheck; REFER preserves unresolved input. Neither terminal is a clinical conclusion.",
    }, started)


def run_batch():
    started = time.perf_counter()
    rows = [core.run_spatial_workflow(fixture) for fixture in core.spatial_fixtures()]
    return _wrap("six_generated_native_space_workflows", {
        "workflows": rows,
        "summary": {"tasks": len(rows), "verified_technical_STOP": sum(row["terminal"] == "STOP" for row in rows),
                    "safe_REFER": sum(row["terminal"] == "REFER" for row in rows),
                    "actual_calls_including_failures": sum(row["calls"] for row in rows),
                    "sample_unit": "generated fixture, not a patient or independent clinical sample"},
    }, started)


def compare_policies(scenario="witness", mode="retain", fixed_observation=False):
    if scenario not in (*SCENARIOS, "all") or mode not in core.MODES or type(fixed_observation) is not bool:
        raise ValueError("Unregistered generated comparison request")
    started = time.perf_counter()
    selected = list(SCENARIOS) if scenario == "all" else [scenario]
    results = []
    for alias in selected:
        task = core.toy_scenarios()[SCENARIOS[alias]]
        for arm in core.ARMS:
            if arm == "strong_one_step_gate":
                actual = core.rolling_one_step_policy(task, mode, fixed_observation)
                row = {"scenario": task.name, "arm": arm, "policy": actual["policy"],
                       "metrics": actual["metrics"], "planning_nodes": actual["planning_nodes"],
                       "actual_wall_seconds": actual["actual_wall_seconds"],
                       "implementation": "True rolling horizon-one replan after each acquired observation; complete root risk rechecked",
                       "root_risk_recomputed": True,
                       "root_infeasible_baseline_fallback": actual["root_infeasible_baseline_fallback"]}
            else:
                row = core.run_toy_comparison(task, arm, mode, fixed_observation)
                row["implementation"] = ("Complete finite planner, intentionally shared with the TACTIC demonstration" if arm in ("finite_complete_VOI", "applicability_aware_controller")
                                         else "Deterministic dependency workflow" if arm == "dependency_aware_deterministic" else "Depth-two finite cascade")
            row.update(scenario_alias=alias, label=ARM_LABELS[arm], observation_mode=mode,
                       fixed_observation=fixed_observation,
                       common_call_budget=task.call_budget, root_mean_loss_cap=task.mean_cap,
                       root_cvar90_loss_cap=task.tail_cap)
            results.append(row)
    return _wrap("declared_finite_policy_comparison", {
        "results": results,
        "interpretation": [
            "The constructed witness yields utility 7 for deterministic/two-step/complete-VOI/TACTIC versus 6 for one-step, when run with the original retain/no-fixed-prefix settings.",
            "This is a declared dimensionless opportunity construction, not clinical efficacy or an independent benchmark.",
            "Strong deterministic and two-step workflows can tie TACTIC. TACTIC uses the complete finite planner here; it is not a new algorithm.",
            "All arms share legal acquired history, actions, tool models, budget and the root risk set; observation ablations are applied across all arms.",
            "The mean and CVaR caps in these witnesses are redundant, not a separable dual-risk innovation.",
        ],
    }, started)


def check_generated_input(case="canonical", mode="full_ensemble", fault="none"):
    started = time.perf_counter()
    if fault == "none":
        request = nifti_guard.make_generated_request(mode, case)
    else:
        candidates = {item["name"]: item for item in nifti_guard.mutation_cases() if not item["expect_pass"]}
        if fault not in candidates:
            raise ValueError("Unregistered generated input fault")
        request = candidates[fault]["request"]
    result = nifti_guard.validate_generated_request(request)
    return _wrap("generated_nifti_input_contract", result, started)


def check_all_inputs():
    started = time.perf_counter()
    cases = []
    for fixture in nifti_guard.mutation_cases():
        result = nifti_guard.validate_generated_request(fixture["request"])
        cases.append({"name": fixture["name"], "expected_pass": fixture["expect_pass"],
                      "actual_pass": result["report"]["passed"], "report": result["report"]})
    return _wrap("generated_nifti_contract_suite", {"cases": cases,
        "all_expected_decisions_matched": all(row["expected_pass"] == row["actual_pass"] for row in cases),
        "passed_inputs_are_not_model_inference": True}, started)


def tool_registry():
    return {"system": BRAND, "internal_controller": INTERNAL_CONTROLLER,
            "generated_tools": ["bounded native-space arithmetic", "evidence applicability store",
                                "finite shared-policy comparison", "strict generated NIfTI input guard"],
            "external_deepisles": nifti_guard.load_registry(), "scope": BOUNDARIES.copy()}


def comparison_rows(report):
    def number(value):
        return value["decimal"] if type(value) is dict and "decimal" in value else value
    return [{"Scenario": row["scenario_alias"], "Policy": row["label"],
             "Utility (toy)": number(row["metrics"]["expected_utility"]),
             "Mean loss (toy)": number(row["metrics"]["mean_loss"]),
             "CVaR90 (toy)": number(row["metrics"]["cvar90_loss"]),
             "Expected calls (toy)": number(row["metrics"]["expected_calls"]),
             "Root-feasible": row["metrics"]["feasible"]}
            for row in report["payload"]["results"]]
