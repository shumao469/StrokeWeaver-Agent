"""Public-safe fixed synthetic demo; no uploads, patient inputs or model calls."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import streamlit as st
from strokeweaver_agent import BRAND, __version__
from strokeweaver_agent import api, audit, nifti_guard, routing


st.set_page_config(page_title="StrokeWeaver Agent", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container{padding-top:2.6rem;max-width:1450px}h1{letter-spacing:-.055em!important;font-weight:750!important}h2,h3{letter-spacing:-.025em!important}
[data-testid="stMetric"]{background:#111e30;border:1px solid #24364d;padding:18px;border-radius:14px}[data-testid="stMetricLabel"]{color:#a9bad1}
.eyebrow{color:#5eead4;text-transform:uppercase;font-size:.72rem;letter-spacing:.19em;font-weight:700}.lede{color:#a9bad1;max-width:820px;font-size:1.04rem;line-height:1.7}
.boundary{border:1px solid #254b55;border-radius:12px;padding:15px 18px;color:#b8d9dd;background:#0d1e2a;font-size:.9rem}
.footnote{font-size:.78rem;color:#8da2bc;line-height:1.6}div.stButton>button{border-radius:10px}pre{font-size:.76rem}
</style>""", unsafe_allow_html=True)


def downloads(report, key):
    left, middle, right = st.columns(3)
    left.download_button("Download audit JSON", audit.to_json(report), file_name="strokeweaver_generated_audit.json", mime="application/json", key=key + "_json")
    middle.download_button("Download readable HTML", audit.to_html(report), file_name="strokeweaver_generated_audit.html", mime="text/html", key=key + "_html")
    right.download_button("Download evidence bundle", audit.export_zip(report), file_name="strokeweaver_generated_bundle.zip", mime="application/zip", key=key + "_zip")
    st.caption("Generated artifacts only. Report hashes bind content, not clinical safety. No server-side export path is accepted.")


with st.sidebar:
    st.markdown("### StrokeWeaver Agent")
    st.caption("TACTIC · internal evidence controller")
    st.divider()
    st.markdown("**SYNTHETIC DEMO**")
    st.success("Patient execution: disabled")
    st.caption("No clinical images, model weights, training, free-form uploads or arbitrary commands.")
    st.divider()
    st.markdown("**Release scope**")
    st.write("Native-space technical QC, bounded repair, provenance and shared-policy comparisons.")
    st.caption(f"Version {__version__} · Research prototype")
    st.markdown("**External imaging model**")
    st.write("DeepISLES is not bundled or executed. Its license, runtime, training exposure and data admission remain separate gates.")
    st.caption("Historical system alias: StrokeWeave. TACTIC is a controller inside this system, not another visual model.")

st.markdown('<div class="eyebrow">Evidence-first research workflows</div>', unsafe_allow_html=True)
st.title("StrokeWeaver Agent")
st.markdown('<p class="lede">Observe what matters. Repair only what is justified. Keep every action traceable.<br>A runnable generated-only prototype for reliable stroke-imaging research software—not autonomous diagnosis or treatment.</p>', unsafe_allow_html=True)
st.markdown('<div class="boundary">All inputs below are fixed, self-generated phantoms. Technical references are not patient lesion truth. Software checks and constructed policy witnesses do not establish clinical accuracy or an independent validation cohort.</div>', unsafe_allow_html=True)
st.write("")
metrics = st.columns(4)
metrics[0].metric("Input scope", "Generated only")
metrics[1].metric("Patient tasks", "Disabled")
metrics[2].metric("Internal controller", "TACTIC")
metrics[3].metric("External model", "Not loaded")

workflow_tab, planning_tab, input_tab, methods_tab = st.tabs(["Native-space workflow", "Shared-policy comparison", "NIfTI input guard", "Methods & boundaries"])

with workflow_tab:
    st.subheader("A complete, bounded technical workflow")
    st.caption("Actual generated binary voxels → input contract → diagnostic observation → conditional software repair → independent recheck → STOP or REFER.")
    controls, viewer = st.columns([1, 1.5], gap="large")
    labels = {
        "correct_native": "Valid native grid", "centimeter_encoded": "Declared centimeter spacing",
        "stale_axis_transform": "Declared axis-order conflict", "invalid_nonbinary": "Non-binary input (reject)",
        "unknown_units": "Unknown spatial units (refer)", "transient_analysis_failure": "One transient tool failure (recover)",
    }
    with controls:
        fixture = st.selectbox("Generated task", api.FIXTURES, index=1, format_func=labels.get, key="fixture_choice")
        preset = st.selectbox("Constrained task preview", ["Run generated volume and geometry QC", "Compare generated repair policies", "Check generated NIfTI input contract"])
        plan = routing.preview(preset)
        st.caption(f"Router: {plan['engine']}")
        st.info(plan["explanation"])
        st.caption("The preview is not an LLM and does not execute. Use the matching tab's explicit run button.")
        if st.button("Run generated workflow", type="primary", key="run_native"):
            st.session_state["native_audit"] = api.run_demo(fixture)
        if st.button("Run all six generated cases", key="run_batch"):
            st.session_state["batch_audit"] = api.run_batch()
    with viewer:
        selected = next(f for f in api.core.spatial_fixtures() if f["name"] == fixture)
        source = selected["input"]
        z = st.slider("Generated source-grid slice", 0, source["shape"][2] - 1, 0)
        st.image(audit.slice_png(source["mask"], source["shape"], z), caption="Fixed generated binary phantom. This is not a patient MRI or neural segmentation.", width=430)
        st.caption(f"Shape {source['shape']} · spacing {source['spacing']} {source['units']} · axes {source['axes']}")
        st.code(api.core.digest(source), language=None)
        st.caption("SHA-256 of the generated input structure; no data are read from an external path.")
    report = st.session_state.get("native_audit")
    if report:
        result = report["payload"]["workflow"]
        a, b, c, d = st.columns(4)
        a.metric("Technical terminal", result["terminal"])
        b.metric("Actual charged calls", result["calls"])
        c.metric("Measured API wall", f"{report['cost']['actual_api_wall_seconds']:.4f} s")
        d.metric("Audit hash", "Valid" if api.verify_audit(report) else "INVALID")
        if result["terminal"] == "REFER":
            st.warning("Unresolved technical input. No result is presented as verified; failure records are retained.")
        else:
            st.success(f"Generated technical recheck passed · volume {result['report']['volume_ml']:.3f} mL. This is spatial arithmetic, not a medical accuracy result.")
        st.caption(f"Displayed audit belongs to: {labels.get(result['fixture'], result['fixture'])}. Changing the selector does not silently rerun it.")
        trace, evidence = st.columns(2)
        with trace:
            st.markdown("#### Action and failure trace")
            st.dataframe(result["trace"], width="stretch", hide_index=True)
        with evidence:
            st.markdown("#### Observed is not adopted")
            st.dataframe(result["evidence"], width="stretch", hide_index=True)
        with st.expander("Complete generated audit and dependency invalidations"):
            st.json(report)
        downloads(report, "native")
    batch = st.session_state.get("batch_audit")
    if batch:
        st.markdown("#### Six-case task summary")
        st.json(batch["payload"]["summary"])
        st.dataframe([{"Fixture": row["fixture"], "Terminal": row["terminal"], "Charged calls": row["calls"]} for row in batch["payload"]["workflows"]], hide_index=True)
        downloads(batch, "batch")

with planning_tab:
    st.subheader("Which decisions add value—and when do they not?")
    st.caption("Declared dimensionless task family. The complete finite VOI and TACTIC demonstration intentionally share the same planner. Ties and negative controls are first-class results.")
    c1, c2, c3 = st.columns(3)
    scenario = c1.selectbox("Declared task family", ["witness", "redundant", "unresolvable", "all"], format_func=lambda s: {"witness": "Diagnostic opportunity witness", "redundant": "Redundant observation: gate-optimal", "unresolvable": "Unresolvable: REFER", "all": "All three families"}[s], key="scenario_choice")
    mode = c2.selectbox("Observation intervention (all arms)", ["retain", "mask", "uninformative"], key="observation_mode")
    fixed = c3.checkbox("Fix an initial observation and sunk cost", value=False, key="fixed_observation")
    if st.button("Run shared-policy comparison", type="primary", key="run_compare"):
        st.session_state["comparison_audit"] = api.compare_policies(scenario, mode, fixed)
    comparison = st.session_state.get("comparison_audit")
    if comparison:
        rows = api.comparison_rows(comparison)
        st.dataframe(rows, width="stretch", hide_index=True)
        if len({row["Scenario"] for row in rows}) == 1:
            st.bar_chart([{"Policy": row["Policy"], "Utility (toy)": row["Utility (toy)"]} for row in rows], x="Policy", y="Utility (toy)", horizontal=True)
        st.info("The original constructed witness yields 7 for deterministic / two-step / full VOI / TACTIC and 6 for rolling one-step. This does not establish superiority over strong deterministic workflows, a new algorithm, or real stroke benefit.")
        st.caption("Expected calls and losses are exact toy-model quantities, not measured clinical latency or patient risk. The original mean and tail caps are mathematically redundant in this family.")
        with st.expander("Complete policy trees, legal histories and root-risk calculations"):
            st.json(comparison)
        downloads(comparison, "compare")

with input_tab:
    st.subheader("Actual NIfTI bytes, explicit applicability")
    st.caption("A strict NIfTI-1 little-endian float32 subset. Generated 4×3×2 inputs only; not a general DICOM reader, actual MRI validation or model invocation.")
    c1, c2 = st.columns(2)
    geometry = c1.selectbox("Generated affine", nifti_guard.CASES, key="geometry_choice")
    tool_mode = c2.selectbox("External tool contract", list(nifti_guard.MODE_MODALITIES), format_func=lambda x: "Full ensemble: DWI + ADC + FLAIR" if x == "full_ensemble" else "SEALS component: DWI + ADC (not full ensemble)", key="tool_mode")
    faults = ["none", *(r["name"] for r in nifti_guard.mutation_cases() if not r["expect_pass"])]
    fault = st.selectbox("Controlled input fault", faults, key="guard_fault")
    if st.button("Validate generated input contract", type="primary", key="run_guard"):
        st.session_state["input_audit"] = api.check_generated_input(geometry, tool_mode, fault)
    if st.button("Run all 23 fixed input-contract cases", key="run_input_suite"):
        st.session_state["input_suite"] = api.check_all_inputs()
    guard = st.session_state.get("input_audit")
    if guard:
        result = guard["payload"]["report"]
        if result["passed"]:
            st.success("Generated INPUT CONTRACT passed. Neural inference remains disabled; no segmentation task is complete.")
        else:
            st.warning("REFER · " + result["error_code"] + ". Unverified image values are not retained as evidence.")
        st.json(result)
        with st.expander("Hash-bound, observed-but-unadopted handover"):
            st.json(guard["payload"]["evidence_handover"])
        downloads(guard, "guard")
    suite = st.session_state.get("input_suite")
    if suite:
        st.dataframe([{"Case": row["name"], "Expected pass": row["expected_pass"], "Actual pass": row["actual_pass"]} for row in suite["payload"]["cases"]], hide_index=True)
        st.caption("These are controlled engineering cases, not clinical samples or new naturally occurring software defects.")
        downloads(suite, "input_suite")

with methods_tab:
    st.subheader("One system, explicit boundaries")
    st.markdown("**StrokeWeaver Agent** is the research system. **TACTIC** is its internal evidence-applicability and conditional-repair controller. The historical name **StrokeWeave** appears only in source provenance.")
    st.markdown("**Implemented:** generated native-space arithmetic and lossless technical repair; dependency invalidation; observed/adopted evidence separation; finite exact shared-policy comparison; true rolling one-step control; STOP/REFER separation; bounded retry; generated NIfTI provenance and geometry guard; in-memory audit export.")
    st.markdown("**Not established:** patient-level or clinical performance; new visual architecture; general multistep algorithmic superiority; independent cohort or cross-tool transfer; physician review burden; clinical risk certification or autonomous treatment.")
    st.warning("The declared opportunity can be solved equally well by a mature deterministic dependency workflow and a two-step cascade. The demo preserves that tie; it does not manufacture an agent-exclusive advantage.")
    st.markdown("**DeepISLES:** external source and weights are not bundled. Full integration requires DWI, ADC and FLAIR. ISLES training exposure must be disclosed. A separately approved runtime, compatible inputs, independent references and lawful data roles are required before patient processing.")
    with st.expander("Tool registry and release source fingerprints"):
        st.json(api.tool_registry())
        st.json(api.source_bindings())
    st.caption("Core computation uses only the Python standard library. Streamlit provides this interface; no browser input grants a model, shell or patient-data capability.")

st.divider()
st.markdown('<p class="footnote">StrokeWeaver Agent · Research software prototype · Generated inputs only · No autonomous clinical use<br>Timing shown is measured software wall time within its stated scope, not a clinical acceleration claim.</p>', unsafe_allow_html=True)
