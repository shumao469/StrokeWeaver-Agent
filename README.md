# StrokeWeaver Agent

StrokeWeaver is a research software project for auditable stroke-imaging workflows. The two project phases are maintained side by side in this repository.

| Project phase | Public software | Start here |
| --- | --- | --- |
| **StrokeWeaver 1.0** | Executable generated-data demo. Native-space checks, conditional repair, shared-policy comparison and audit exports. | [Documentation and quick start](StrokeWeaver-1.0/README.md) |
| **StrokeWeaver 2.0** | Evidence Workbench and local read-only MCP for the audited generated MRI and local-model qualification. Replay standard completion, stale-evidence referral and interruption recovery. | [Documentation and quick start](StrokeWeaver-2.0/README.md) |

[中文说明](README.zh-CN.md) · [Licensing status](LICENSE_STATUS.md) · [Security and research boundaries](SECURITY.md)

The existing [hosted Streamlit demo](https://strokeweaver-agent.streamlit.app/) serves StrokeWeaver 1.0 through the root entrypoint. Run the 2.0 Evidence Workbench locally using its own quick start. The public repository uses generated inputs and recorded technical outcomes. Model weights, patient data, protected labels and clinical execution are outside the public distribution.
