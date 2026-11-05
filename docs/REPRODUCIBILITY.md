# Reproducibility and evidence boundaries

## Public reproducible scope

This repository regenerates fixed synthetic inputs and runs owned software. It does not reproduce private patient training, re-open protected datasets, rerun old exposed patient comparisons or download external model weights.

```bash
python -m unittest discover -s tests -v
python examples/reproduce.py
python run.py demo --fixture all
python run.py compare --scenario all --mode retain
python run.py input-check --all-cases
```

Run tests in the same isolated Python environment used for the application. Install `requirements.txt` to include the optional Streamlit smoke test; otherwise document the skipped UI test. Do not report an old test count as a fresh result. Test counts and timing repeats are not independent research subjects.

The 2026-11-05 release receipt records 70 tests passed with exit code 0, including Streamlit AppTest. Its captured child wall was about 12.73 seconds, while the unittest runner reported about 12.10 seconds; these have different scopes and are not application-speed benchmarks. The test receipt binds the tested package/UI source hashes. This public-package test run is distinct from historical V2 engineering-check counts and does not imply visual browser acceptance.

## Core mechanism witness

The default witness has utility 7 for the deterministic workflow, strong two-step, complete finite VOI and TACTIC; qualified true rolling one-step has 6. The redundant scenario ties at 7.25. The unresolvable scenario returns REFER.

These are exact expectations over a declared small model. There is no sampling uncertainty to replace with fabricated error bars. They demonstrate that nonmyopic opportunities can exist, but also that a mature simple dependency workflow can reach the same value. TACTIC shares the finite planner with full VOI; the result is not a new algorithm or unique framework advantage.

The toy risk units are not Dice, lesion volume, treatment harm or a transferable clinical budget. The mean and tail caps are redundant in this family. A valid toy policy does not certify unknown-model or patient safety.

## Observation mechanism intervention

```bash
python run.py compare --scenario witness --mode retain --fixed-observation
python run.py compare --scenario witness --mode mask --fixed-observation
python run.py compare --scenario witness --mode uninformative --fixed-observation
```

An acquired initial observation and its cost are fixed. The original witness yields 7 with retention and 5.75 for masking/uninformative content across all five arms. The retained route also makes additional paid calls. This is an information intervention, not a claim of cheaper total runtime or exclusive TACTIC memory.

Without `--fixed-observation`, the execution setting differs; do not silently mix the resulting numbers or compare different budgets as one experiment. Main policy comparisons share all legal history. Always report the actual selected scenario, intervention, fixed-observation setting and source commit.

## Generated native-space and input checks

Six registered spatial fixtures cover known unit/context/input/failure cases. Their references are arithmetic construction values, not expert lesion labels. A STOP means that generated technical task passed; a REFER preserves an unresolved issue and does not measure human workload.

The NIfTI guard suite contains 23 controlled cases: four compatible generated inputs and nineteen expected typed rejections. It uses actual binary NIfTI bytes in a strict small format subset. Positive acceptance does not establish general NIfTI/DICOM compatibility, biological registration, usable brain tissue, motion quality or model inference. This public repository does not bundle the older private third-party decoder runtime.

## Report integrity and timing

Generated audits contain the implementation source bindings, scope, payload and a content SHA-256. `api.verify_audit(report)` detects inconsistency with that stored digest; an actor able to alter both payload and digest can recompute it. It is not a signature, institutional approval or clinical safety guarantee.

`cost.actual_api_wall_seconds` measures the Python task and package provenance hashing. It excludes CLI/UI startup, rendering, downloading and hosting. Expected toy calls are not observed clinical latency. Do not infer a full-task runtime ratio, GPU efficiency or cost superiority from the demo's small runtimes.

Reports serialize timestamps and timings, so complete JSON hashes can differ across otherwise equivalent reruns. Compare the defined task outputs, policy metrics, source bindings and scope—not byte identity of fresh timing-bearing reports. Frozen historical receipts remain separate records.

## Historical evidence: preserve corrections as well as positives

The project has earlier controlled engineering evidence, including a real-artifact R1 experiment with 216 paired forks following one shared generated DeepISLES model prefix. Those forks are not 216 neural inferences or patients. Mature workflow, gate and conditional one-step VOI outcomes were identical; no public-demo superiority claim follows from that historical experiment. Third-party model/runtime material is not included here.

Legacy C3 learning produced a negative artifact, retained without retroactive success editing. A later joint-world posterior and unified payoff-accounting repair suspended its earlier “exact reference equals rolling” interpretation. Corrected old conditions were exposed debugging cases, not new validation, and the learned model was not rerun against the repaired reference. Do not reproduce the old numbers as a currently valid upper-bound comparison or pool old and corrected task semantics.

`legacy/source_index.json` records the small curated owned-source subset and adaptation descriptions. It does not expose protected histories, labels, rosters or private environment bindings, and it is not a request to rerun all historical work.

## Before any real-data extension

Require a prospective lawful task role, source/version rights, anonymous patient/exam and repeat semantics, historical/protected-role exclusion, checkpoint training exposure, actual input/native-space QC and independently authorized reference geometry/semantics. Then lock task-specific endpoints, risk rules, budgets and shared strong baselines before outcomes are viewed.

Online technical verification must never read sealed evaluation truth. Scientific scoring belongs after immutable candidate submission and remains separate from planning, memory, thresholds and repair. Clinical tasks and treatment recommendations are outside this release.

## Reporting results

Report the commit, Python/dependency versions, exact generated command, expected versus actual terminal, scoped counts/costs and known limitations. Accept ties, negative controls and expected refusals. Do not claim clinical accuracy, new network architecture, global optimality outside the finite graph, general memory novelty, independent patient validation or journal readiness from this package.

For issues, attach only minimal generated reproductions and sanitized logs. Never submit patient images, protected outputs, dataset access keys, credentials or tokens.
