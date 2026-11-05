"""Generated-only unit definitions; executing them does not access patient data."""

from dataclasses import replace
from fractions import Fraction
import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from strokeweaver_agent.controller import (
    ARMS, Context, ContractError, EvidenceStore, FinitePlanner,
    GeneratedSpatialTask, ToyState, _transpose, _volume, cvar_root,
    digest, evidence_for, evaluate_policy_root, execute_toy_policy,
    legal_options, run_spatial_workflow, run_toy_comparison,
    run_rolling_gate_qualification, rolling_one_step_policy,
    spatial_fixtures, toy_scenarios, toy_step,
)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.context = Context(digest({"generated": True}))
        self.store = EvidenceStore(self.context)

    def add(self, key="a", dependencies=()):
        payload = {"value": 1}
        self.store.register(key, evidence_for(self.context, payload, ("report", "diagnose"), dependencies), payload)

    def test_observed_not_adopted_remains_useful(self):
        self.add()
        self.assertTrue(self.store.applicable("a", "diagnose"))
        self.assertFalse(self.store.records["a"].adopted)

    def test_adopt_requires_current_operation(self):
        self.add()
        with self.assertRaises(ContractError):
            self.store.adopt("a", "unknown")
        self.store.adopt("a", "report")
        self.assertTrue(self.store.records["a"].adopted)

    def test_unknown_unobserved_and_duplicate(self):
        self.assertFalse(self.store.applicable("future"))
        self.add()
        with self.assertRaises(ContractError):
            self.add()
        record = replace(evidence_for(self.context, {}, ("report",)), observed=False)
        with self.assertRaises(ContractError):
            self.store.register("future", record, {})

    def test_hash_failure(self):
        with self.assertRaises(ContractError):
            self.store.register("a", evidence_for(self.context, {"x": 1}, ("report",)), {"x": 2})

    def test_tampered_dependency(self):
        self.add()
        self.add("b", ("a",))
        self.store.payloads["a"]["value"] = 2
        self.assertFalse(self.store.applicable("b"))

    def test_context_invalidation_preserves_history(self):
        self.add()
        self.add("b", ("a",))
        self.store.adopt("b", "report")
        self.store.change_context(replace(self.context, transform_version="v2"))
        self.assertFalse(self.store.applicable("a"))
        self.assertFalse(self.store.applicable("b"))
        self.assertTrue(self.store.records["b"].adopted)
        self.assertTrue(self.store.records["b"].observed)

    def test_missing_dependency_rejected(self):
        with self.assertRaises(ContractError):
            self.add(dependencies=("not_acquired",))

    def test_wrong_timepoint_units_modality_space_input(self):
        for field, value in (("timepoint", "future"), ("units", "cm"), ("space", "other"),
                             ("modality", "CT"), ("input_sha256", "0" * 64)):
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.store.register(field, replace(evidence_for(self.context, {}, ("report",)), **{field: value}), {})

    def test_invalid_metadata_only(self):
        metadata = {"error_code": "TIMEOUT", "action": "inspect", "attempt": 1}
        record = evidence_for(self.context, metadata, ("technical_failure",), validity="invalid")
        self.store.register("failure", record, None, metadata)
        self.assertIsNone(self.store.payloads["failure"])
        self.assertFalse(self.store.applicable("failure"))
        with self.assertRaises(ContractError):
            self.store.register("leak", record, {"unverified_volume": 4}, metadata)

    def test_failure_arbitrary_payload_metadata_blocked(self):
        metadata = {"error_code": "FAIL", "unverified_volume": 7}
        record = evidence_for(self.context, metadata, ("technical_failure",), validity="invalid")
        with self.assertRaises(ContractError):
            self.store.register("failure", record, None, metadata)

    def test_nonfinite_payload_rejected(self):
        with self.assertRaises(ValueError):
            evidence_for(self.context, {"x": float("nan")}, ("report",))


class SpatialTests(unittest.TestCase):
    def test_exact_volume_units(self):
        self.assertEqual(_volume((1, 0), (2, 1, 1), (2, 3, 4), "mm"), Fraction(3, 125))
        self.assertEqual(_volume((1, 0), (2, 1, 1), (.2, .3, .4), "cm"), Fraction(3, 125))

    def test_axis_permutation_roundtrip(self):
        mask = tuple(range(24))
        transformed, shape = _transpose(mask, (4, 3, 2), (2, 1, 0))
        restored, restored_shape = _transpose(transformed, shape, (2, 1, 0))
        self.assertEqual(restored, mask)
        self.assertEqual(restored_shape, (4, 3, 2))

    def test_geometry_not_just_volume(self):
        fixture = next(f for f in spatial_fixtures() if f["name"] == "stale_axis_transform")
        task = GeneratedSpatialTask(fixture)
        task.apply("initial_analysis")
        result = task.apply("recheck")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(task.terminal(), "REFER")

    def test_good_and_repairable_outputs(self):
        for fixture in spatial_fixtures()[:3]:
            result = run_spatial_workflow(fixture)
            self.assertEqual(result["terminal"], "STOP")
            self.assertEqual(result["report"]["volume_ml"], .072)
            self.assertLessEqual(result["calls"], 4)

    def test_ambiguous_and_bad_binary_refer(self):
        for fixture in [f for f in spatial_fixtures() if f["name"] in ("invalid_nonbinary", "unknown_units")]:
            result = run_spatial_workflow(fixture)
            self.assertEqual(result["terminal"], "REFER")
            self.assertIsNone(result["report"])

    def test_no_diagnosis_no_repair(self):
        task = GeneratedSpatialTask(spatial_fixtures()[1])
        result = task.apply("conditional_repair")
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(task.store.payloads["failure_1"])

    def test_budgets_include_failed_attempts(self):
        task = GeneratedSpatialTask(spatial_fixtures()[0], budget=1)
        task.apply("conditional_repair")
        self.assertEqual(task.calls, 1)
        with self.assertRaises(ContractError):
            task.apply("initial_analysis")

    def test_single_transient_failure_recovered_with_record_preserved(self):
        fixture = next(f for f in spatial_fixtures() if f["name"] == "transient_analysis_failure")
        result = run_spatial_workflow(fixture)
        self.assertEqual(result["terminal"], "STOP")
        self.assertEqual(result["calls"], 3)
        self.assertEqual([r["attempt"] for r in result["trace"][:2]], [1, 2])
        self.assertTrue(any(e["key"] == "failure_1" and not e["applicable"] for e in result["evidence"]))

    def test_no_unbounded_same_action_retry(self):
        task = GeneratedSpatialTask(spatial_fixtures()[0])
        task.apply("conditional_repair")
        task.apply("conditional_repair")
        with self.assertRaisesRegex(ContractError, "RECOVERY_ATTEMPT_EXHAUSTED"):
            task.apply("conditional_repair")
        self.assertEqual(task.calls, 2)

    def test_stale_diagnostic_not_adopted_after_repair(self):
        task = GeneratedSpatialTask(spatial_fixtures()[2])
        task.apply("initial_analysis")
        task.apply("diagnose_conflict")
        self.assertTrue(task.store.applicable("diagnostic_observation", "repair_selection"))
        task.apply("conditional_repair")
        self.assertFalse(task.store.applicable("diagnostic_observation"))
        self.assertFalse(task.store.records["diagnostic_observation"].adopted)
        task.apply("recheck")
        self.assertEqual(task.terminal(), "STOP")

    def test_unknown_unit_nan_spacing_nonbinary(self):
        for mask, spacing, units in (((1,), (1, 1, 1), "?"), ((1,), (1, float("nan"), 1), "mm"), ((2,), (1, 1, 1), "mm")):
            with self.assertRaises(ContractError):
                _volume(mask, (1, 1, 1), spacing, units)


class PlanningTests(unittest.TestCase):
    def test_two_step_analytic_witness(self):
        scenario = toy_scenarios()[0]
        one = FinitePlanner(scenario).plan(1)
        two = FinitePlanner(scenario).plan(2)
        full = FinitePlanner(scenario).plan(5)
        self.assertEqual(one["metrics"]["expected_utility"], 6)
        self.assertEqual(two["metrics"]["expected_utility"], 7)
        self.assertEqual(full["metrics"]["expected_utility"], 7)

    def test_all_depths_and_macro_costs(self):
        scenario = toy_scenarios()[0]
        for depth in range(1, 6):
            result = FinitePlanner(scenario).plan(depth)
            self.assertEqual(result["metrics"]["expected_utility"], 6 if depth == 1 else 7)
            self.assertTrue(all(o["calls"] <= 3 for o in result["metrics"]["outcomes"]))

    def test_redundant_gate_optimal(self):
        scenario = toy_scenarios()[1]
        self.assertEqual(FinitePlanner(scenario).plan(1)["metrics"]["expected_utility"], Fraction(29, 4))
        self.assertEqual(FinitePlanner(scenario).plan(5)["metrics"]["expected_utility"], Fraction(29, 4))

    def test_unresolvable_refer(self):
        scenario = toy_scenarios()[2]
        for arm in ARMS:
            row = run_toy_comparison(scenario, arm)
            self.assertTrue(all(o["terminal"] == "REFER" for o in row["metrics"]["outcomes"]))

    def test_stop_not_allowed_without_report(self):
        with self.assertRaises(ContractError):
            evaluate_policy_root(toy_scenarios()[2], {"action": "STOP"})

    def test_risk_is_root_tail_not_average_child_tail(self):
        losses = [(Fraction(0), Fraction(19, 20)), (Fraction(1), Fraction(1, 20))]
        self.assertEqual(cvar_root(losses), Fraction(1, 2))
        self.assertNotEqual(cvar_root(losses), Fraction(1, 20))

    def test_shared_resources_all_arms(self):
        for scenario in toy_scenarios():
            rows = [run_toy_comparison(scenario, arm) for arm in ARMS]
            self.assertEqual(len({r["shared_contract_sha256"] for r in rows}), 1)
            self.assertTrue(all(r["metrics"]["feasible"] for r in rows))

    def test_mature_dependency_workflow_can_tie(self):
        scenario = toy_scenarios()[0]
        deterministic = run_toy_comparison(scenario, ARMS[0])
        full = run_toy_comparison(scenario, "finite_complete_VOI")
        self.assertEqual(deterministic["metrics"]["expected_utility"], full["metrics"]["expected_utility"])

    def test_no_future_observation_in_execution(self):
        scenario = toy_scenarios()[0]
        policy = FinitePlanner(scenario).plan(5)["policy"]
        for world in scenario.worlds:
            result = execute_toy_policy(scenario, world, policy)
            for index, row in enumerate(result["trace"]):
                self.assertEqual(len(row["acquired_history_before"]), index)
            self.assertEqual(result["trace"][0]["acquired_history_before"], ())
            self.assertFalse(result["trace"][0]["adopted_as_edit"])

    def test_retained_vs_mask_same_sunk_calls(self):
        scenario = toy_scenarios()[0]
        retained = run_toy_comparison(scenario, "finite_complete_VOI", "retain", True)
        masked = run_toy_comparison(scenario, "finite_complete_VOI", "mask", True)
        noinfo = run_toy_comparison(scenario, "finite_complete_VOI", "uninformative", True)
        self.assertEqual(retained["metrics"]["expected_utility"], 7)
        self.assertEqual(masked["metrics"]["expected_utility"], Fraction(23, 4))
        self.assertEqual(masked["metrics"]["expected_utility"], noinfo["metrics"]["expected_utility"])
        self.assertTrue(all(o["trace"][0]["action"] == "INSPECT" for row in (retained, masked, noinfo) for o in row["metrics"]["outcomes"]))

    def test_invalid_depth_modes_and_actions(self):
        scenario = toy_scenarios()[0]
        for depth in (0, 6, True):
            with self.assertRaises(ContractError):
                FinitePlanner(scenario).plan(depth)
        with self.assertRaises(ContractError):
            FinitePlanner(scenario, "future")
        with self.assertRaises(ContractError):
            toy_step(scenario, scenario.worlds[0], ToyState(), "FUTURE_TOOL")

    def test_true_rolling_gate_route_equality_in_locked_family(self):
        for scenario in toy_scenarios():
            for mode in ("retain", "mask", "uninformative"):
                for fixed_prefix in (False, True):
                    row = run_rolling_gate_qualification(scenario, mode, fixed_prefix)
                    self.assertTrue(row["exact_executed_routes_and_outcomes_equal"])
                    self.assertTrue(row["root_risk_recomputed"])
                    self.assertTrue(row["rolling_metrics"]["feasible"])

    def test_true_rolling_replans_after_acquired_observation(self):
        scenario = toy_scenarios()[1]
        result = rolling_one_step_policy(scenario)
        self.assertGreaterEqual(result["replanning_decisions"], 2)
        self.assertEqual(result["metrics"]["expected_utility"], Fraction(29, 4))
        self.assertTrue(all(o["history"] == (("REPAIR_A", "RECHECK_PASS"),) for o in result["metrics"]["outcomes"]))


if __name__ == "__main__":
    unittest.main()
