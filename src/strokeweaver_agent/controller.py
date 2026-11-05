"""StrokeWeaver Agent's TACTIC generated-only internal controller.

Release adaptation of the project-owned 2026-11-05 generated repair core.
The byte-exact historical implementation is indexed under legacy/.
No patient/file/model access is added by this portable copy.

Two separate objects are intentional:
* GeneratedSpatialTask performs actual bounded binary-array/metric operations.
* finite toy planning measures a declared, dimensionless opportunity witness.
Neither supplies clinical accuracy, an independent patient cohort, or novelty.
"""

from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import product
import copy
import hashlib
import json
import math
import time


ARMS = (
    "dependency_aware_deterministic", "strong_one_step_gate",
    "strong_two_step_cascade", "finite_complete_VOI",
    "applicability_aware_controller",
)
MODES = ("retain", "mask", "uninformative")


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha(value):
    return (isinstance(value, str) and len(value) == 64 and
            all(c in "0123456789abcdef" for c in value))


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class Context:
    input_sha256: str
    modality: str = "GENERATED_BINARY_ARRAY"
    timepoint: str = "generated_t0"
    space: str = "native_xyz"
    transform_version: str = "identity_v1"
    units: str = "mm"


@dataclass(frozen=True)
class Evidence:
    source: str
    tool_version: str
    input_sha256: str
    output_sha256: str
    modality: str
    timepoint: str
    space: str
    transform_version: str
    units: str
    valid_for: tuple
    dependencies: tuple
    observed: bool = True
    adopted: bool = False
    validity: str = "valid"


def evidence_for(context, payload, valid_for, dependencies=(), *,
                 source="generated_tool", validity="valid"):
    return Evidence(source, "1", context.input_sha256, digest(payload),
                    context.modality, context.timepoint, context.space,
                    context.transform_version, context.units,
                    tuple(valid_for), tuple(dependencies), True, False, validity)


class EvidenceStore:
    """Hash-bound observations; adoption, applicability and validity differ.

An invalid output is never retained as numerical evidence. Its only payload is
None and its SHA binds a controlled technical-failure metadata dictionary.
An old-context record is preserved, invalidated, and may not become current
evidence merely because it was previously adopted.
"""

    def __init__(self, context):
        if not _sha(context.input_sha256):
            raise ContractError("BAD_INPUT_HASH")
        self.context = context
        self.records = {}
        self.payloads = {}
        self.metadata = {}
        self.invalidation_log = []

    def _matches(self, record, context):
        return all(getattr(record, field) == getattr(context, field) for field in
                   ("input_sha256", "modality", "timepoint", "space",
                    "transform_version", "units"))

    def register(self, key, record, payload, failure_metadata=None):
        if key in self.records or not isinstance(key, str) or not key:
            raise ContractError("DUPLICATE_OR_INVALID_EVIDENCE_KEY")
        if not isinstance(record, Evidence) or not record.observed:
            raise ContractError("UNOBSERVED_EVIDENCE")
        if record.adopted or not _sha(record.output_sha256):
            raise ContractError("BAD_NEW_RECORD")
        if not record.source or not record.tool_version or not record.valid_for:
            raise ContractError("MISSING_PROVENANCE")
        if not self._matches(record, self.context):
            raise ContractError("CONTEXT_MISMATCH")
        if record.validity == "valid":
            if failure_metadata is not None or digest(payload) != record.output_sha256:
                raise ContractError("PAYLOAD_HASH_MISMATCH")
            for dependency in record.dependencies:
                if dependency not in self.records or not self.applicable(dependency):
                    raise ContractError("UNAVAILABLE_DEPENDENCY")
        elif record.validity == "invalid":
            if payload is not None or not isinstance(failure_metadata, dict):
                raise ContractError("INVALID_OUTPUT_METADATA_ONLY")
            if set(failure_metadata) - {"error_code", "action", "attempt"}:
                raise ContractError("FAILURE_METADATA_NOT_ALLOWLISTED")
            if not isinstance(failure_metadata.get("error_code"), str):
                raise ContractError("FAILURE_ERROR_CODE_REQUIRED")
            if record.dependencies or digest(failure_metadata) != record.output_sha256:
                raise ContractError("FAILURE_HASH_OR_DEPENDENCIES")
        else:
            raise ContractError("UNKNOWN_VALIDITY")
        self.records[key] = record
        self.payloads[key] = copy.deepcopy(payload)
        self.metadata[key] = copy.deepcopy(failure_metadata)

    def applicable(self, key, operation=None, _seen=None):
        record = self.records.get(key)
        if record is None or not record.observed or record.validity != "valid":
            return False
        if not self._matches(record, self.context):
            return False
        if operation is not None and operation not in record.valid_for:
            return False
        try:
            if digest(self.payloads[key]) != record.output_sha256:
                return False
        except (ValueError, TypeError):
            return False
        seen = set() if _seen is None else set(_seen)
        if key in seen:
            return False
        seen.add(key)
        return all(self.applicable(dep, _seen=seen) for dep in record.dependencies)

    def adopt(self, key, operation):
        if not self.applicable(key, operation):
            raise ContractError("INAPPLICABLE_ADOPTION")
        self.records[key] = replace(self.records[key], adopted=True)

    def invalidate(self, key, reason):
        if key not in self.records:
            raise ContractError("UNKNOWN_EVIDENCE")
        pending = [key]
        visited = set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            self.records[current] = replace(self.records[current], validity="invalid")
            self.invalidation_log.append({"key": current, "reason": reason})
            pending.extend(k for k, r in self.records.items() if current in r.dependencies)

    def change_context(self, context):
        if not _sha(context.input_sha256):
            raise ContractError("BAD_CONTEXT_HASH")
        self.context = context
        for key in tuple(self.records):
            if self.records[key].validity == "valid" and not self._matches(self.records[key], context):
                self.invalidate(key, "CONTEXT_CHANGED_REVALIDATION_REQUIRED")

    def summary(self):
        return [{"key": k, "observed": r.observed, "adopted": r.adopted,
                 "validity": r.validity, "applicable": self.applicable(k),
                 "output_sha256": r.output_sha256, "dependencies": list(r.dependencies)}
                for k, r in sorted(self.records.items())]


def _volume(mask, shape, spacing, units):
    if len(shape) != 3 or any(type(x) is not int or x < 1 or x > 16 for x in shape):
        raise ContractError("BAD_SHAPE")
    if len(mask) != math.prod(shape) or any(type(x) is not int or x not in (0, 1) for x in mask):
        raise ContractError("NONBINARY_OR_SHAPE_MISMATCH")
    if len(spacing) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0
                                for x in spacing):
        raise ContractError("BAD_SPACING")
    if units not in ("mm", "cm"):
        raise ContractError("UNKNOWN_UNITS_NO_IMPUTATION")
    scale = Fraction(1) if units == "mm" else Fraction(10)
    voxel = math.prod(Fraction(str(x)) * scale for x in spacing)
    return Fraction(sum(mask)) * voxel / 1000


def _transpose(mask, shape, order):
    if sorted(order) != [0, 1, 2]:
        raise ContractError("BAD_AXIS_PERMUTATION")
    newshape = tuple(shape[i] for i in order)
    out = []
    for x in range(newshape[0]):
        for y in range(newshape[1]):
            for z in range(newshape[2]):
                old = [0, 0, 0]
                for i, value in enumerate((x, y, z)):
                    old[order[i]] = value
                out.append(mask[(old[0] * shape[1] + old[1]) * shape[2] + old[2]])
    return tuple(out), newshape


def spatial_fixtures():
    """Small, entirely self-generated arrays; no files or medical models."""
    shape = (4, 3, 2)
    mask = tuple(int(i in (3, 8, 22)) for i in range(math.prod(shape)))
    canonical = {"mask": mask, "shape": shape, "spacing": (2, 3, 4),
                 "units": "mm", "axes": ("x", "y", "z")}
    fixtures = []
    for name in ("correct_native", "centimeter_encoded", "stale_axis_transform",
                 "invalid_nonbinary", "unknown_units", "transient_analysis_failure"):
        data = copy.deepcopy(canonical)
        if name == "centimeter_encoded":
            data.update(spacing=(0.2, 0.3, 0.4), units="cm")
        elif name == "stale_axis_transform":
            data["mask"], data["shape"] = _transpose(mask, shape, (2, 1, 0))
            data.update(spacing=(4, 3, 2), axes=("z", "y", "x"))
        elif name == "invalid_nonbinary":
            data["mask"] = (2,) + mask[1:]
        elif name == "unknown_units":
            data["units"] = "unknown"
        fixtures.append({"name": name, "input": data,
                         "technical_reference": copy.deepcopy(canonical)})
    return fixtures


class GeneratedSpatialTask:
    """Actual array/metric work. Reference is used only by independent recheck.

    No neural model is called. A repair is only a lossless units conversion or
    array-axis permutation identified from the acquired technical observation.
    """

    def __init__(self, fixture, budget=4):
        if type(budget) is not int or budget < 1 or budget > 4:
            raise ContractError("BUDGET_RANGE")
        self.fixture = copy.deepcopy(fixture)
        self.data = copy.deepcopy(fixture["input"])
        context = Context(digest(fixture["input"]), units=self.data["units"],
                          space="native_xyz" if self.data["axes"] == ("x", "y", "z") else "encoded_axes",
                          transform_version="identity_v1" if self.data["axes"] == ("x", "y", "z") else "stale_v0")
        self.store = EvidenceStore(context)
        self.budget = budget
        self.calls = 0
        self.trace = []
        self.attempts = {}
        self.transient_failures_remaining = int(fixture["name"] == "transient_analysis_failure")
        self.analysis = None
        self.diagnosis = None
        self.report = None

    def _register(self, key, payload, operations, dependencies=()):
        record = evidence_for(self.store.context, payload, operations, dependencies)
        self.store.register(key, record, payload)

    def _failure(self, action, error_code):
        metadata = {"action": action, "error_code": error_code, "attempt": self.attempts[action]}
        record = evidence_for(self.store.context, metadata, ("technical_failure",),
                              validity="invalid")
        self.store.register("failure_" + str(self.calls), record, None, metadata)
        return {"status": "failed", "error_code": error_code}

    def apply(self, action):
        if action not in ("initial_analysis", "diagnose_conflict", "conditional_repair", "recheck"):
            raise ContractError("UNKNOWN_ACTION")
        if self.calls >= self.budget:
            raise ContractError("BUDGET_EXHAUSTED")
        if self.attempts.get(action, 0) >= 2:
            raise ContractError("ONE_RECOVERY_ATTEMPT_EXHAUSTED")
        start = time.perf_counter()
        self.calls += 1
        self.attempts[action] = self.attempts.get(action, 0) + 1
        try:
            if action == "initial_analysis":
                if self.transient_failures_remaining:
                    self.transient_failures_remaining -= 1
                    raise ContractError("GENERATED_TRANSIENT_TOOL_FAILURE")
                vol = _volume(self.data["mask"], self.data["shape"], self.data["spacing"], self.data["units"])
                payload = {"volume_ml": float(vol), "shape": self.data["shape"],
                           "canonical_contract": self.data["units"] == "mm" and self.data["axes"] == ("x", "y", "z")}
                self.analysis = payload
                self._register("initial_analysis", payload, ("technical_diagnosis",))
                result = {"status": "ok", **payload}
            elif action == "diagnose_conflict":
                if self.analysis is None:
                    raise ContractError("ANALYSIS_NOT_ACQUIRED")
                self.diagnosis = {"convert_cm_to_mm": self.data["units"] == "cm",
                                  "axis_order": tuple(self.data["axes"].index(a) for a in ("x", "y", "z"))}
                self._register("diagnostic_observation", self.diagnosis, ("repair_selection",), ("initial_analysis",))
                result = {"status": "ok", **self.diagnosis, "adopted_as_edit": False}
            elif action == "conditional_repair":
                if self.diagnosis is None or not self.store.applicable("diagnostic_observation", "repair_selection"):
                    raise ContractError("DIAGNOSIS_NOT_ACQUIRED_OR_STALE")
                source_hash = digest(self.data)
                if self.diagnosis["convert_cm_to_mm"]:
                    self.data["spacing"] = tuple(float(Fraction(str(x)) * 10) for x in self.data["spacing"])
                    self.data["units"] = "mm"
                order = self.diagnosis["axis_order"]
                if order != (0, 1, 2):
                    self.data["mask"], self.data["shape"] = _transpose(self.data["mask"], self.data["shape"], order)
                    self.data["spacing"] = tuple(self.data["spacing"][i] for i in order)
                    self.data["axes"] = ("x", "y", "z")
                # Old observations stay archived but must not certify a new context.
                newctx = replace(self.store.context, units=self.data["units"],
                                 space="native_xyz", transform_version="generated_lossless_repair_v1")
                self.store.change_context(newctx)
                proof = {"source_artifact_sha256": source_hash, "repaired_sha256": digest(self.data),
                         "algorithm": "declared_unit_scale_and_axis_permutation_v1"}
                self._register("repair_revalidation", proof, ("repair_provenance",))
                self._register("repaired_candidate", {"artifact_sha256": digest(self.data)},
                               ("independent_recheck",), ("repair_revalidation",))
                result = {"status": "ok", "candidate_sha256": digest(self.data), "adopted_as_edit": False}
            else:
                ref = self.fixture["technical_reference"]
                actual = _volume(self.data["mask"], self.data["shape"], self.data["spacing"], self.data["units"])
                expected = _volume(ref["mask"], ref["shape"], ref["spacing"], ref["units"])
                geometry_ok = (self.data["shape"] == ref["shape"] and self.data["axes"] == ref["axes"] and
                               all(Fraction(str(x)) == Fraction(str(y)) for x, y in zip(self.data["spacing"], ref["spacing"])) and
                               self.data["units"] == ref["units"])
                if not geometry_ok or tuple(self.data["mask"]) != tuple(ref["mask"]) or actual != expected:
                    raise ContractError("INDEPENDENT_TECHNICAL_REFERENCE_MISMATCH")
                deps = ("repaired_candidate",) if "repaired_candidate" in self.store.records else ("initial_analysis",)
                payload = {"volume_ml": float(actual), "geometry_pass": True,
                           "artifact_sha256": digest(self.data), "reference_scope": "SELF_GENERATED_TECHNICAL_ARRAY_ONLY"}
                self._register("independent_recheck", payload, ("report",), deps)
                self.store.adopt("independent_recheck", "report")
                self.report = payload
                result = {"status": "ok", **payload}
        except (ContractError, ValueError, TypeError, IndexError) as exc:
            code = str(exc) if isinstance(exc, ContractError) else "MALFORMED_GENERATED_INPUT"
            result = self._failure(action, code)
        elapsed = time.perf_counter() - start
        self.trace.append({"action": action, "status": result["status"],
                           "attempt": self.attempts[action],
                           "calls_after": self.calls, "wall_seconds": elapsed,
                           "observation_sha256": digest(result), "observation": result})
        return copy.deepcopy(result)

    def terminal(self):
        if self.report is not None and self.store.applicable("independent_recheck", "report"):
            return "STOP"
        return "REFER"


def run_spatial_workflow(fixture):
    task = GeneratedSpatialTask(fixture)
    observed = task.apply("initial_analysis")
    if observed.get("error_code") == "GENERATED_TRANSIENT_TOOL_FAILURE":
        observed = task.apply("initial_analysis")
    if observed["status"] == "ok":
        if not observed["canonical_contract"]:
            diagnosis = task.apply("diagnose_conflict")
            if diagnosis["status"] == "ok":
                task.apply("conditional_repair")
        if task.calls < task.budget:
            task.apply("recheck")
    return {"fixture": fixture["name"], "terminal": task.terminal(), "calls": task.calls,
            "report": task.report, "trace": task.trace, "evidence": task.store.summary(),
            "invalidation_log": task.store.invalidation_log,
            "wall_seconds": sum(row["wall_seconds"] for row in task.trace),
            "real_neural_inference": False, "patient_execution": False}


@dataclass(frozen=True)
class ToyWorld:
    name: str
    fault: str
    probability: Fraction


@dataclass(frozen=True)
class ToyScenario:
    name: str
    worlds: tuple
    baseline_valid: bool = True
    repairable: bool = True
    call_budget: int = 3
    mean_cap: Fraction = Fraction(1, 4)
    tail_cap: Fraction = Fraction(1, 4)


@dataclass(frozen=True)
class ToyState:
    calls: int = 0
    cost_quarters: int = 0
    inspected: bool = False
    attempted: tuple = ()
    improved: bool = False
    history: tuple = ()


def toy_scenarios():
    return (
        ToyScenario("diagnosis_then_conditional_repair_witness",
                    (ToyWorld("a", "A", Fraction(1, 2)), ToyWorld("b", "B", Fraction(1, 2)))),
        ToyScenario("redundant_observation_gate_optimal", (ToyWorld("a", "A", Fraction(1)),)),
        ToyScenario("ambiguous_unresolvable_REFER",
                    (ToyWorld("u", "UNKNOWN", Fraction(1)),), baseline_valid=False,
                    repairable=False, mean_cap=Fraction(1, 2), tail_cap=Fraction(1, 2)),
    )


def legal_options(scenario, state):
    options = []
    if not state.inspected and state.calls + 1 <= scenario.call_budget and not state.improved:
        options.append("INSPECT")
    if state.calls + 2 <= scenario.call_budget and not state.improved:
        options.extend("REPAIR_" + fault for fault in ("A", "B") if fault not in state.attempted)
    return tuple(options)


def toy_step(scenario, world, state, action, mode="retain"):
    if mode not in MODES or action not in legal_options(scenario, state):
        raise ContractError("ILLEGAL_TOY_ACTION")
    if action == "INSPECT":
        observation = world.fault if mode == "retain" else "UNKNOWN"
        return replace(state, calls=state.calls + 1, cost_quarters=state.cost_quarters + 1,
                       inspected=True, history=state.history + ((action, observation),)), observation
    chosen = action[-1]
    passed = scenario.repairable and chosen == world.fault
    observation = "RECHECK_PASS" if passed else "RECHECK_FAIL_METADATA_ONLY"
    return replace(state, calls=state.calls + 2, cost_quarters=state.cost_quarters + 11,
                   attempted=state.attempted + (chosen,), improved=passed or state.improved,
                   history=state.history + ((action, observation),)), observation


def _terminal_metrics(scenario, state, action):
    if action == "STOP":
        if not state.improved and not scenario.baseline_valid:
            raise ContractError("STOP_WITHOUT_VERIFIED_REPORT")
        value, loss = (Fraction(10), Fraction(0)) if state.improved else (Fraction(6), Fraction(1, 4))
    elif action == "REFER":
        value, loss = Fraction(0), Fraction(1, 2)
    else:
        raise ContractError("NONTERMINAL_METRICS")
    return value - Fraction(state.cost_quarters, 4), loss


def cvar_root(losses, alpha=Fraction(9, 10)):
    """Exact weighted upper-tail CVaR on root outcome distribution."""
    remaining = 1 - alpha
    if remaining <= 0 or remaining > 1 or sum(p for _, p in losses) != 1:
        raise ContractError("BAD_ROOT_DISTRIBUTION")
    total = Fraction(0)
    for loss, probability in sorted(losses, key=lambda row: row[0], reverse=True):
        take = min(remaining, probability)
        total += take * loss
        remaining -= take
        if remaining == 0:
            break
    return total / (1 - alpha)


def _execute_toy_from_state(scenario, world, policy, state, mode):
    node = policy
    trace = []
    for _ in range(6):
        action = node["action"]
        before_history = state.history
        if action in ("STOP", "REFER"):
            utility, loss = _terminal_metrics(scenario, state, action)
            return {"world": world.name, "probability": world.probability,
                    "utility": utility, "loss": loss, "calls": state.calls,
                    "terminal": action, "history": state.history, "trace": trace}
        state, observation = toy_step(scenario, world, state, action, mode)
        trace.append({"action": action, "acquired_history_before": before_history,
                      "observation": observation, "calls_after": state.calls,
                      "adopted_as_edit": action != "INSPECT" and observation == "RECHECK_PASS"})
        node = node["branches"][observation]
    raise ContractError("POLICY_DID_NOT_TERMINATE")


def execute_toy_policy(scenario, world, policy, mode="retain"):
    return _execute_toy_from_state(scenario, world, policy, ToyState(), mode)


def evaluate_policy_root(scenario, policy, mode="retain"):
    outcomes = [execute_toy_policy(scenario, world, policy, mode) for world in scenario.worlds]
    if sum(row["probability"] for row in outcomes) != 1:
        raise ContractError("WORLD_PROBABILITIES")
    utility = sum(row["probability"] * row["utility"] for row in outcomes)
    mean = sum(row["probability"] * row["loss"] for row in outcomes)
    tail = cvar_root([(row["loss"], row["probability"]) for row in outcomes])
    calls = sum(row["probability"] * row["calls"] for row in outcomes)
    return {"expected_utility": utility, "mean_loss": mean, "cvar90_loss": tail,
            "expected_calls": calls, "outcomes": outcomes,
            "feasible": mean <= scenario.mean_cap and tail <= scenario.tail_cap}


class FinitePlanner:
    """Enumerate bounded contingent policies, then filter WHOLE-root risk.

    Models, actions, evidence, macros, cache rules and risk set are shared by
    every arm. In this tiny family the applicability controller deliberately
    uses the same exhaustive solver as finite VOI; it is not a new method.
    """

    def __init__(self, scenario, mode="retain"):
        if mode not in MODES:
            raise ContractError("BAD_OBSERVATION_MODE")
        self.scenario = scenario
        self.mode = mode
        self.nodes = 0
        self._memo = {}

    def _enumerate(self, belief, depth):
        key = (belief, depth)
        if key in self._memo:
            return self._memo[key]
        self.nodes += 1
        representative = belief[0][1]
        if any(state.history != representative.history or state.calls != representative.calls
               for _, state in belief):
            raise ContractError("BELIEF_MERGED_DISTINGUISHABLE_HISTORIES")
        policies = [{"action": "REFER"}]
        if representative.improved or self.scenario.baseline_valid:
            policies.append({"action": "STOP"})
        if depth > 0:
            for action in legal_options(self.scenario, representative):
                groups = {}
                for index, state in belief:
                    updated, observation = toy_step(self.scenario, self.scenario.worlds[index], state, action, self.mode)
                    groups.setdefault(observation, []).append((index, updated))
                names = sorted(groups)
                children = [self._enumerate(tuple(groups[name]), depth - 1) for name in names]
                for combination in product(*children):
                    policies.append({"action": action,
                                     "branches": {name: child for name, child in zip(names, combination)}})
        self._memo[key] = tuple(policies)
        return self._memo[key]

    def policies(self, horizon, fixed_initial_observation=False):
        if type(horizon) is not int or not 1 <= horizon <= 5:
            raise ContractError("PLANNING_DEPTH_RANGE")
        initial = tuple((index, ToyState()) for index in range(len(self.scenario.worlds)))
        if not fixed_initial_observation:
            return self._enumerate(initial, horizon)
        groups = {}
        for index, state in initial:
            updated, observation = toy_step(self.scenario, self.scenario.worlds[index], state, "INSPECT", self.mode)
            groups.setdefault(observation, []).append((index, updated))
        names = sorted(groups)
        children = [self._enumerate(tuple(groups[name]), horizon) for name in names]
        return tuple({"action": "INSPECT", "branches": dict(zip(names, combination))}
                     for combination in product(*children))

    def plan(self, horizon=5, fixed_initial_observation=False):
        start = time.perf_counter()
        policies = self.policies(horizon, fixed_initial_observation)
        feasible = []
        for policy in policies:
            metrics = evaluate_policy_root(self.scenario, policy, self.mode)
            if metrics["feasible"]:
                feasible.append((policy, metrics))
        if not feasible:
            raise ContractError("NO_FEASIBLE_POLICY")
        best_utility = max(metrics["expected_utility"] for _, metrics in feasible)
        finalists = [(p, m) for p, m in feasible if m["expected_utility"] == best_utility]
        policy, metrics = min(finalists, key=lambda pair: (pair[1]["expected_calls"], canonical_bytes(pair[0])))
        return {"policy": policy, "metrics": metrics, "enumerated_policies": len(policies),
                "feasible_policies": len(feasible), "planning_nodes": self.nodes,
                "planning_wall_seconds": time.perf_counter() - start,
                "scope": "EXACT_WITHIN_THIS_EXPLICIT_FINITE_GENERATED_GRAPH_ONLY"}


def _conditional_policy_metrics(scenario, policy, belief, mode):
    """One-step lookahead at acquired history, not access to the true world.

    The belief contains all worlds compatible with the actual observable
    history; their publicly declared priors are normalized. Sunk calls/cost
    remain in the supplied states. Local filtering is not advertised as a
    guarantee on executed whole-policy root risk.
    """
    mass = sum(scenario.worlds[index].probability for index, _ in belief)
    if mass <= 0:
        raise ContractError("ZERO_CONDITIONAL_BELIEF")
    outcomes = []
    for index, state in belief:
        world = scenario.worlds[index]
        row = _execute_toy_from_state(scenario, world, policy, state, mode)
        row["probability"] = world.probability / mass
        outcomes.append(row)
    mean = sum(row["probability"] * row["loss"] for row in outcomes)
    tail = cvar_root([(row["loss"], row["probability"]) for row in outcomes])
    return {"expected_utility": sum(row["probability"] * row["utility"] for row in outcomes),
            "expected_calls": sum(row["probability"] * row["calls"] for row in outcomes),
            "mean_loss": mean, "cvar90_loss": tail,
            "feasible": mean <= scenario.mean_cap and tail <= scenario.tail_cap}


def rolling_one_step_policy(scenario, mode="retain", fixed_initial_observation=False):
    """True rolling one-step replan after EACH actual possible observation.

    This constructs the executed contingent policy from legal compatible
    histories, not a preselected fixed one-layer tree. Every replan scores
    exactly one option plus a terminal action. The resulting complete policy
    is independently root-evaluated; an infeasible result falls back to the
    same verified baseline, preserving any fixed sunk observation cost.
    This toy construction is not an online population-risk guarantee.
    """
    if mode not in MODES:
        raise ContractError("BAD_OBSERVATION_MODE")
    start = time.perf_counter()
    planner = FinitePlanner(scenario, mode)
    counters = {"replanning_decisions": 0, "candidate_policies_evaluated": 0}
    memo = {}

    def branch_after(action, belief):
        groups = {}
        for index, state in belief:
            updated, observation = toy_step(scenario, scenario.worlds[index], state, action, mode)
            groups.setdefault(observation, []).append((index, updated))
        return {observation: continuation(tuple(group)) for observation, group in sorted(groups.items())}

    def continuation(belief):
        if belief in memo:
            return memo[belief]
        counters["replanning_decisions"] += 1
        candidates = planner._enumerate(belief, 1)
        counters["candidate_policies_evaluated"] += len(candidates)
        feasible = []
        for policy in candidates:
            metrics = _conditional_policy_metrics(scenario, policy, belief, mode)
            if metrics["feasible"]:
                feasible.append((policy, metrics))
        if not feasible:
            result = {"action": "STOP" if scenario.baseline_valid or belief[0][1].improved else "REFER"}
        else:
            best = max(m["expected_utility"] for _, m in feasible)
            selected, _ = min(((p, m) for p, m in feasible if m["expected_utility"] == best),
                              key=lambda pair: (pair[1]["expected_calls"], canonical_bytes(pair[0])))
            action = selected["action"]
            result = ({"action": action} if action in ("STOP", "REFER") else
                      {"action": action, "branches": branch_after(action, belief)})
        memo[belief] = result
        return result

    initial = tuple((index, ToyState()) for index in range(len(scenario.worlds)))
    baseline = {"action": "STOP" if scenario.baseline_valid else "REFER"}
    if fixed_initial_observation:
        policy = {"action": "INSPECT", "branches": branch_after("INSPECT", initial)}
        observations = {w.fault if mode == "retain" else "UNKNOWN" for w in scenario.worlds}
        baseline = {"action": "INSPECT", "branches": {obs: baseline for obs in observations}}
    else:
        policy = continuation(initial)
    metrics = evaluate_policy_root(scenario, policy, mode)
    fallback = not metrics["feasible"]
    if fallback:
        policy = baseline
        metrics = evaluate_policy_root(scenario, policy, mode)
        if not metrics["feasible"]:
            raise ContractError("ROLLING_BASELINE_NOT_ROOT_FEASIBLE")
    return {"policy": policy, "metrics": metrics, "root_risk_recomputed": True,
            "root_infeasible_baseline_fallback": fallback,
            "replanning_decisions": counters["replanning_decisions"],
            "candidate_policies_evaluated": counters["candidate_policies_evaluated"],
            "planning_nodes": planner.nodes,
            "actual_wall_seconds": time.perf_counter() - start}


def run_rolling_gate_qualification(scenario, mode="retain", fixed_initial_observation=False):
    rolling = rolling_one_step_policy(scenario, mode, fixed_initial_observation)
    fixed = run_toy_comparison(scenario, "strong_one_step_gate", mode, fixed_initial_observation)

    def executed_signature(metrics):
        return [{key: row[key] for key in ("world", "probability", "utility", "loss", "calls", "terminal", "history", "trace")}
                for row in metrics["outcomes"]]

    equivalent = executed_signature(fixed["metrics"]) == executed_signature(rolling["metrics"])
    return {"scenario": scenario.name, "observation_mode": mode,
            "fixed_initial_observation": fixed_initial_observation,
            "fixed_one_layer_policy": fixed["policy"], "rolling_policy": rolling["policy"],
            "fixed_metrics": fixed["metrics"], "rolling_metrics": rolling["metrics"],
            "exact_executed_routes_and_outcomes_equal": equivalent,
            "root_risk_recomputed": rolling["root_risk_recomputed"],
            "root_infeasible_baseline_fallback": rolling["root_infeasible_baseline_fallback"],
            "replanning_decisions": rolling["replanning_decisions"],
            "candidate_policies_evaluated": rolling["candidate_policies_evaluated"],
            "planning_nodes": rolling["planning_nodes"],
            "actual_wall_seconds": rolling["actual_wall_seconds"],
            "scope": "ROUTE_EQUIVALENCE_IF_PASSED_ONLY_FOR_THIS_DECLARED_GENERATED_FAMILY"}


def deterministic_policy(scenario, mode="retain", fixed_initial_observation=False):
    """A mature hand-coded dependency workflow can tie finite planning here."""
    terminal = {"action": "STOP" if scenario.baseline_valid else "REFER"}

    def repair(which):
        return {"action": "REPAIR_" + which,
                "branches": {"RECHECK_PASS": {"action": "STOP"},
                             "RECHECK_FAIL_METADATA_ONLY": terminal}}

    if not scenario.repairable:
        return {"action": "INSPECT", "branches": {"UNKNOWN": terminal}} if fixed_initial_observation else terminal
    if not fixed_initial_observation and len({w.fault for w in scenario.worlds}) == 1:
        return repair(scenario.worlds[0].fault)
    observations = {w.fault if mode == "retain" else "UNKNOWN" for w in scenario.worlds}
    return {"action": "INSPECT", "branches": {
        obs: repair(obs) if obs in ("A", "B") else terminal for obs in observations}}


def run_toy_comparison(scenario, arm, mode="retain", fixed_initial_observation=False):
    if arm not in ARMS:
        raise ContractError("UNKNOWN_ARM")
    start = time.perf_counter()
    if arm == "dependency_aware_deterministic":
        policy = deterministic_policy(scenario, mode, fixed_initial_observation)
        details = {"planning_nodes": 0, "enumerated_policies": 1, "feasible_policies": 1}
    else:
        horizon = 1 if arm == "strong_one_step_gate" else 2 if arm == "strong_two_step_cascade" else 5
        details = FinitePlanner(scenario, mode).plan(horizon, fixed_initial_observation)
        policy = details["policy"]
    metrics = evaluate_policy_root(scenario, policy, mode)
    return {"scenario": scenario.name, "arm": arm, "observation_mode": mode,
            "fixed_initial_observation": fixed_initial_observation,
            "policy": policy, "policy_sha256": digest(policy), "metrics": metrics,
            "planning_nodes": details["planning_nodes"],
            "enumerated_policies": details["enumerated_policies"],
            "feasible_policies": details["feasible_policies"],
            "actual_wall_seconds": time.perf_counter() - start,
            "shared_contract_sha256": digest({"budget": scenario.call_budget,
                "mean_cap": str(scenario.mean_cap), "tail_cap": str(scenario.tail_cap),
                "options": ["INSPECT", "REPAIR_A_PLUS_RECHECK", "REPAIR_B_PLUS_RECHECK", "STOP", "REFER"],
                "history_access": "ALL_ACQUIRED_SUCCESSFUL_OBSERVATIONS", "recovery_attempts": 1}),
            "dimensionless_toy_only": True}


def json_safe(value):
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator,
                "decimal": float(value)}
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(v) for v in value]
    return value
