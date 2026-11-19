# Reproducing the StrokeWeaver research demonstration

This guide describes the public release and its relationship to the manuscript experiments. The release uses self-generated inputs and previously recorded technical receipts. Data access and model weights have their own terms and are not distributed in this repository.

## Version and basic checks

For the recorded public workbench and evidence package, use the source revision [d35520a2b364720cf62e457337a877df7b7ae1ef](https://github.com/shumao469/StrokeWeaver-Agent/tree/d35520a2b364720cf62e457337a877df7b7ae1ef). This identifier freezes the public replay version, not the private training environment or every manuscript experiment.

```bash
git clone https://github.com/shumao469/StrokeWeaver-Agent.git
cd StrokeWeaver-Agent
git checkout d35520a2b364720cf62e457337a877df7b7ae1ef
cd StrokeWeaver-2.0
python -B verify_release.py
```

The verification checks the bundled manifest and replay records, then runs the read-only MCP service as a subprocess. For the recorded package, the expected scenario terminals are `STOP`, `REFER` and `STOP`, with 17 MCP checks. The command validates the published receipts and the current MCP implementation. It does not rerun the vision model or language model used to generate those receipts.

The optional workbench uses Python 3.11 or newer and the pinned dependency in `workbench/requirements.txt`. Follow the [2.0 quick start](README.md) to inspect the recorded event timelines and export a scenario report. For executable synthetic fixtures and finite-policy witness examples, use the [1.0 reproduction commands](../StrokeWeaver-1.0/docs/REPRODUCIBILITY.md).

## Components and evidence

| Component | Role in the recorded study | Material in the public release |
| --- | --- | --- |
| Task specification and coordinator | Identify the generated modalities, sequence tool calls and record task status | Protocol, scenario traces and reports |
| Image worker | Produced a native-grid score in the original controlled qualification | Receipt; model checkpoint and original execution runtime are separate |
| Evidence guard | Checked artifact identity, native geometry and task context | Recorded checks, digests, review and event traces |
| Local language model | Requested the allowlisted status tool in normal and recovered scenarios | Recorded exchanges and outcomes; model runtime is separate |
| Analytic controllers | Compared actions in explicitly specified finite models | Selected generated demonstration policies in 1.0; the full manuscript experiment bundle is separate |
| Human handoff | Recorded `REFER` and a pending review for stale evidence | Read-only recorded handoff; no reviewer action is simulated |

The three 2.0 workbench routes are archived replays. The 1.0 examples execute the distributed generated-data software, but they have their own fixtures and are not a fresh run of the manuscript's full finite-model study.

## What the public package can reproduce

| Manuscript evidence | Available public check | Additional material required to regenerate the reported figure |
| --- | --- | --- |
| Figure 1a and 1d, SOOP and generated workbench | The 2.0 replay verifies the recorded completion, invalidation and recovery traces in Fig. 1d | Fig. 1a needs the applicable SOOP data, native-space processing and the study's frozen TinyUNet checkpoint. The source image example and the generated replay are separate. |
| Figure 1e and Fig. 2d, DeepISLES | The public workbench records a technical replay; the image benchmark was published by the DeepISLES authors | The original published DeepISLES outputs and benchmark are described in [de la Rosa et al.](https://doi.org/10.1038/s41467-025-62373-x). Regeneration requires the original cohort, its reference annotations and the authors' model setup. |
| Figure 2, SOOP QC and component execution | The 1.0 demo includes small generated geometry and failure fixtures | The reported 12-pair QC and the full DeepISLES runtime need the corresponding study environment and source inputs. |
| Figure 3, finite-policy and recovery comparisons | The 1.0 witness runs its documented synthetic policy examples | The reported 32 parameter settings across three memory conditions and the DeepISLES-prefix fork study require their original locked study configurations and result artifacts. |
| Figure 4 and Supplementary Fig. 2, shared inference and timing | The public repository documents the workflow but distributes no frozen TinyUNet checkpoint | Regeneration requires the study checkpoint, worker, generated inputs and timed environment. The reported comparisons used five generated inputs and four policy branches. |
| Figure 5, APIS source-development ranking and recorded workbench paths | The 2.0 manifest and traces allow inspection of the three recorded workbench paths | The action-ranking curves require the authorized APIS source-development data, action traces, model outputs and analysis code. |
| Extended Data Figs. 1–3 and Supplementary Fig. 1 | The public demo provides related generated examples | The manuscript's full condition matrices, policy comparisons, score arrays and specific audit suite are separate study artifacts. |

This table reports what is present in this revision. It does not equate related public demonstrations with independent reproduction of a manuscript panel.

## Data and external software

- SOOP v1.1.2 is available at [OpenNeuro ds004889](https://openneuro.org/datasets/ds004889/versions/1.1.2). Its data and study roles should be checked against the relevant release and protocol.
- The APIS dataset is available through the [APIS challenge registration](https://bivl2ab.uis.edu.co/challenges/apis); the [data descriptor](https://doi.org/10.1038/s41598-024-71273-x) explains the access route.
- The [ISLES 2022 dataset descriptor](https://doi.org/10.1038/s41597-022-01875-5) and [ISLES 2024 dataset descriptor](https://doi.org/10.1148/ryai.250603) describe the imaging releases and their access conditions.
- The Johns Hopkins cohort is described by [Liu et al.](https://doi.org/10.1038/s41597-023-02457-9). The DeepISLES paper reports the evaluation subset and its benchmark.
- [DeepISLES source and access instructions](https://github.com/ezequieldlrosa/DeepIsles) are maintained by its authors. The complete configuration uses DWI, ADC and FLAIR; installation instructions, model access and external dependencies are governed by that project.
- The study's TinyUNet checkpoint and original model runtime are not included in this release. Availability and any applicable reuse conditions should be confirmed with the study authors.
- The original 2.0 local language-model qualification used [Llama 3.2 3B through Ollama](https://ollama.com/library/llama3.2:3b). The public workbench replays the audited status exchange and does not require that model.

## Timing scopes and study configuration

The paired Fig. 4 experiment used five generated TRACE/ADC inputs and four policy branches. Shared inference used five model forwards across the inputs; per-policy recomputation used 20. The measured summed strategy intervals were 10.00 s and 27.39 s, respectively. The result is specific to this controlled execution and its timing boundary. The host-level campaign total was 73.63 s, including preflight, launch and verification. It is not a clinical end-to-end estimate.

The frozen paired run recorded PyTorch `2.11.0+cu128`, NumPy `1.26.4`, SciPy `1.15.3` and nibabel `5.4.2`, with GPU inference under the approved generated-input resource policy. The separate 2.0 closed-loop protocol used a CPU worker with two Torch threads and an isolated Ollama `llama3.2:3b` process. Its maximum was three calls, two attempts per operation and 120 seconds per scenario. Actual availability, hardware load, versions and first-run setup affect fresh timings.

Outputs and audit records support technical reproducibility. They do not by themselves establish lesion accuracy, clinical utility, expert review burden or real-world patient safety.
