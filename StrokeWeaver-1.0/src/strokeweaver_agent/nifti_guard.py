"""Portable StrokeWeaver generated NIfTI input contract, not model inference.

Adapted from the project-owned generated adapter. The private runtime paths and
historical-file reader have deliberately been removed from this public package.

No NIfTI library, model import, paths supplied by callers, DICOM conversion,
neural inference, installation, GPU or patient admission is implemented here.
An accepted adapter request is not an accepted lesion segmentation result.
"""

import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct


HERE = Path(__file__).resolve().parent
MAX_BYTES = 2 * 1024 * 1024
MAX_AXIS = 64
MAX_VOXELS = 64 ** 3
GENERATOR = "strokeweave_generated_nifti1_le_f32_v1"
SEED = 20261105
CASES = ("canonical", "left_handed", "oblique")
MODE_MODALITIES = {"full_ensemble": ("DWI", "ADC", "FLAIR"),
                   "SEALS_component": ("DWI", "ADC")}
SOURCE_COMMIT = "7658b608fc0d890cf14448ff3e58c47ad5c761e7"


class InputContractError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_sha(value):
    return sha(canonical(value))


def _require(condition, code):
    if not condition:
        raise InputContractError(code)


def _determinant(matrix):
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _inverse(matrix):
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    det = _determinant(matrix)
    _require(math.isfinite(det) and abs(det) > 1e-9, "SINGULAR_OR_UNBOUNDED_AFFINE")
    result = [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
              [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
              [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]
    condition = max(sum(abs(v) for v in row) for row in matrix) * max(sum(abs(v) for v in row) for row in result)
    _require(math.isfinite(condition) and condition <= 1e6, "ILL_CONDITIONED_AFFINE")
    return result, det, condition


def _matvec(matrix, vector):
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


def geometry_contract(shape, spacing, affine):
    _require(len(affine) == 4 and all(len(row) == 4 for row in affine), "AFFINE_SHAPE")
    _require(all(type(v) in (int, float) and math.isfinite(v) for row in affine for v in row), "NONFINITE_AFFINE")
    _require(tuple(affine[3]) == (0, 0, 0, 1), "AFFINE_HOMOGENEOUS_ROW")
    matrix = [list(row[:3]) for row in affine[:3]]
    inverse, determinant, condition = _inverse(matrix)
    norms = [math.sqrt(sum(matrix[row][column] ** 2 for row in range(3))) for column in range(3)]
    _require(all(math.isclose(x, y, rel_tol=1e-6, abs_tol=1e-5) for x, y in zip(norms, spacing)),
             "PIXDIM_AFFINE_CONFLICT")
    corners = list(itertools.product(*[(0, n - 1) for n in shape]))
    corners.append(tuple((n - 1) / 2 for n in shape))
    worlds = []
    largest_error = 0.0
    origin = [row[3] for row in affine[:3]]
    for coordinate in corners:
        transformed = [v + origin[i] for i, v in enumerate(_matvec(matrix, coordinate))]
        restored = _matvec(inverse, [v - origin[i] for i, v in enumerate(transformed)])
        error = max(abs(a - b) for a, b in zip(coordinate, restored))
        largest_error = max(largest_error, error)
        _require(error <= 1e-6, "COORDINATE_INVERSE_ROUNDTRIP")
        worlds.append(transformed)
    return {"determinant_mm3": determinant, "voxel_volume_mm3": abs(determinant),
            "infinity_condition_estimate": condition,
            "coordinate_roundtrip_max_abs_voxel_error": largest_error,
            "voxel_center_world_bounds_mm": [[min(v[i] for v in worlds), max(v[i] for v in worlds)] for i in range(3)],
            "coordinate_convention": "NIFTI_RAS_MM_VOXEL_CENTERS",
            "whole_brain_coverage_proved": False, "biological_registration_proved": False}


def parse_nifti1_generated(content):
    """Parse real binary bytes, never paths; explicitly a strict format subset."""
    _require(type(content) is bytes, "BYTES_ONLY_NO_PATH_INTERFACE")
    _require(352 <= len(content) <= MAX_BYTES, "BOUNDED_NIFTI_LENGTH")
    _require(content[:2] != b"\x1f\x8b", "COMPRESSED_NIFTI_UNSUPPORTED")
    _require(struct.unpack_from("<i", content, 0)[0] == 348, "NIFTI1_LITTLE_ENDIAN_HEADER_REQUIRED")
    _require(content[344:348] == b"n+1\0", "SINGLE_FILE_NIFTI_MAGIC_REQUIRED")
    dim = struct.unpack_from("<8h", content, 40)
    _require(dim[0] == 3 and tuple(dim[4:]) == (1, 1, 1, 1), "STRICT_3D_REQUIRED")
    shape = tuple(dim[1:4])
    _require(all(1 <= n <= MAX_AXIS for n in shape) and math.prod(shape) <= MAX_VOXELS, "DIMENSION_BOUNDS")
    datatype, bitpix = struct.unpack_from("<2h", content, 70)
    _require((datatype, bitpix) == (16, 32), "FLOAT32_DATATYPE_AND_BITPIX_REQUIRED")
    pixdim = struct.unpack_from("<8f", content, 76)
    _require(all(math.isfinite(v) for v in pixdim) and pixdim[0] == 1 and all(v > 0 for v in pixdim[1:4]), "PIXDIM_FINITE_POSITIVE_REQUIRED")
    _require(tuple(pixdim[4:]) == (1, 1, 1, 1), "NO_EXTRA_DIMENSION_SPACING")
    offset, slope, intercept = struct.unpack_from("<3f", content, 108)
    _require(offset == 352 and content[348:352] == b"\0" * 4, "NO_EXTENSIONS_OFFSET_352_REQUIRED")
    _require(slope == 1 and intercept == 0, "NONIDENTITY_OR_UNDEFINED_SCALING_UNSUPPORTED")
    _require(content[123] == 2, "SPATIAL_MM_NO_TEMPORAL_UNITS_REQUIRED")
    qform, sform = struct.unpack_from("<2h", content, 252)
    _require(qform == 0 and sform == 1, "SCANNER_SFORM_ONLY_SUBSET_REQUIRED")
    _require(all(v == 0 for v in struct.unpack_from("<6f", content, 256)), "UNUSED_QFORM_FIELDS_MUST_BE_ZERO")
    _require(content[148:228].rstrip(b"\0") == b"STROKEWEAVE_GENERATED_V1" and
             content[228:252] == b"\0" * 24 and content[328:344] == b"\0" * 16,
             "GENERATED_HEADER_FIELDS_REQUIRED")
    _require(all(v == 0 for v in struct.unpack_from("<3f", content, 56)) and
             struct.unpack_from("<h", content, 68)[0] == 0 and
             struct.unpack_from("<h", content, 74)[0] == 0 and
             struct.unpack_from("<h", content, 120)[0] == 0 and content[122] == 0 and
             all(v == 0 for v in struct.unpack_from("<4f", content, 124)) and
             struct.unpack_from("<2i", content, 140) == (0, 0), "UNUSED_HEADER_NUMERIC_FIELDS_MUST_BE_ZERO")
    affine = [list(struct.unpack_from("<4f", content, 280 + 16 * row)) for row in range(3)] + [[0, 0, 0, 1]]
    payload = content[352:]
    count = math.prod(shape)
    _require(len(payload) == count * 4, "PAYLOAD_LENGTH_SHAPE_MISMATCH")
    finite_count = 0
    for (value,) in struct.iter_unpack("<f", payload):
        _require(math.isfinite(value), "NONFINITE_VOXEL")
        finite_count += 1
    geometry = geometry_contract(shape, pixdim[1:4], affine)
    return {"shape": list(shape), "spacing_mm": list(pixdim[1:4]), "affine": affine,
            "voxel_count": count, "finite_voxel_count": finite_count,
            "content_bytes": len(content), "content_sha256": sha(content), "payload_sha256": sha(payload),
            "datatype": "NIFTI_TYPE_FLOAT32", "bitpix": 32, "spatial_units": "mm",
            "scaling_applied": False, **geometry}


def _case_affine(case):
    if case == "canonical":
        return [[2, 0, 0, -4], [0, 2.5, 0, -5], [0, 0, 3, -6], [0, 0, 0, 1]]
    if case == "left_handed":
        return [[-2, 0, 0, 4], [0, 2.5, 0, -5], [0, 0, 3, -6], [0, 0, 0, 1]]
    if case == "oblique":
        angle = math.pi / 6
        return [[2 * math.cos(angle), -2.5 * math.sin(angle), 0, -4],
                [2 * math.sin(angle), 2.5 * math.cos(angle), 0, -5],
                [0, 0, 3, -6], [0, 0, 0, 1]]
    raise InputContractError("UNKNOWN_GENERATED_CASE")


def make_generated_nifti(modality, case="canonical"):
    _require(modality in ("DWI", "ADC", "FLAIR"), "UNSUPPORTED_MODALITY")
    affine = _case_affine(case)
    shape = (4, 3, 2)
    spacing = [math.sqrt(sum(affine[row][column] ** 2 for row in range(3))) for column in range(3)]
    header = bytearray(352)
    struct.pack_into("<i", header, 0, 348)
    struct.pack_into("<8h", header, 40, 3, *shape, 1, 1, 1, 1)
    struct.pack_into("<2h", header, 70, 16, 32)
    struct.pack_into("<8f", header, 76, 1, *spacing, 1, 1, 1, 1)
    struct.pack_into("<3f", header, 108, 352, 1, 0)
    header[123] = 2
    header[148:148 + len(b"STROKEWEAVE_GENERATED_V1")] = b"STROKEWEAVE_GENERATED_V1"
    struct.pack_into("<2h", header, 252, 0, 1)
    for row in range(3):
        struct.pack_into("<4f", header, 280 + row * 16, *affine[row])
    header[344:348] = b"n+1\0"
    offset = {"DWI": 11, "ADC": 37, "FLAIR": 83}[modality]
    values = [float(((index * 13 + offset + SEED) % 257) + 1) for index in range(math.prod(shape))]
    return bytes(header) + struct.pack("<" + "f" * len(values), *values)


def make_generated_request(mode="full_ensemble", case="canonical"):
    _require(mode in MODE_MODALITIES and case in CASES, "UNKNOWN_MODE_OR_CASE")
    request = {"schema": "strokeweave-generated-deepisles-request-v1", "mode": mode,
               "generated_only": True, "patient_data": False,
               "study_id": "generated-study-001", "timepoint": "generated-t0",
               "space": "generated_native_RAS", "transform_version": "generated_affine_v1",
               "coverage_scope": "ACQUIRED_VOLUME_ONLY_NO_WHOLE_BRAIN_CLAIM",
               "generator": {"version": GENERATOR, "seed": SEED, "case": case}, "images": {}}
    for modality in MODE_MODALITIES[mode]:
        content = make_generated_nifti(modality, case)
        metadata = {"modality": modality, "study_id": request["study_id"],
                    "series_id": "generated-series-" + modality.lower(),
                    "timepoint": request["timepoint"], "space": request["space"],
                    "transform_version": request["transform_version"], "units": "mm",
                    "intensity_unit": "GENERATED_ARBITRARY_UNIT_NOT_CLINICAL_ADC",
                    "DWI_b_value_declaration": 1000 if modality == "DWI" else None}
        request["images"][modality] = {"content": content, "sha256": sha(content), "metadata": metadata}
    return request


def load_registry():
    """Read the bundled metadata-only registry; no external runtime is loaded."""
    path = HERE / "tool_registry.json"
    _require(not path.is_symlink(), "REGISTRY_SYMLINK_FORBIDDEN")
    raw = path.read_bytes()
    _require(len(raw) <= 65536, "REGISTRY_BOUNDS")
    registry = json.loads(raw)
    _require(registry.get("schema") == "strokeweave-deepisles-input-registry-v1" and
             registry.get("upstream_commit") == SOURCE_COMMIT and
             registry.get("inference_dispatch_allowed") is False and
             registry.get("patient_admission") is False, "REGISTRY_SCOPE_MISMATCH")
    for mode, modalities in MODE_MODALITIES.items():
        _require(tuple(registry["modes"][mode]["required_modalities"]) == modalities and
                 registry["modes"][mode]["this_adapter_inference_qualified"] is False,
                 "REGISTRY_MODE_CONTRACT_MISMATCH")
    return registry


def _validate(request, registry):
    allowed = {"schema", "mode", "generated_only", "patient_data", "study_id", "timepoint",
               "space", "transform_version", "coverage_scope", "generator", "images"}
    _require(type(request) is dict and set(request) == allowed, "EXACT_REQUEST_SCHEMA_NO_PATHS")
    _require(request["schema"] == "strokeweave-generated-deepisles-request-v1", "REQUEST_SCHEMA")
    _require(request["generated_only"] is True and request["patient_data"] is False, "GENERATED_ONLY_REQUIRED")
    _require(registry.get("upstream_commit") == SOURCE_COMMIT and registry.get("inference_dispatch_allowed") is False and
             registry.get("patient_admission") is False, "REGISTRY_SCOPE_MISMATCH")
    mode = request["mode"]
    _require(mode in MODE_MODALITIES, "UNKNOWN_TOOL_MODE")
    modalities = MODE_MODALITIES[mode]
    _require(type(request["images"]) is dict and set(request["images"]) == set(modalities), "MODALITY_SET_MISMATCH")
    _require(request["coverage_scope"] == "ACQUIRED_VOLUME_ONLY_NO_WHOLE_BRAIN_CLAIM", "ACQUIRED_VOLUME_SCOPE_REQUIRED")
    generator = request["generator"]
    _require(type(generator) is dict and set(generator) == {"version", "seed", "case"} and
             generator["version"] == GENERATOR and type(generator["seed"]) is int and generator["seed"] == SEED and
             generator["case"] in CASES, "GENERATOR_RECIPE_REQUIRED")
    expected = make_generated_request(mode, generator["case"])
    for field in ("study_id", "timepoint", "space", "transform_version"):
        _require(request[field] == expected[field], "GENERATED_CONTEXT_REQUIRED")
    summaries = {}
    for modality in modalities:
        item = request["images"][modality]
        _require(type(item) is dict and set(item) == {"content", "sha256", "metadata"}, "EXACT_IMAGE_SCHEMA_NO_PATHS")
        _require(type(item["content"]) is bytes and type(item["sha256"]) is str, "BYTES_AND_HASH_REQUIRED")
        _require(len(item["content"]) <= MAX_BYTES and sha(item["content"]) == item["sha256"], "CONTENT_HASH_MISMATCH")
        meta = item["metadata"]
        _require(type(meta) is dict and set(meta) == set(expected["images"][modality]["metadata"]), "IMAGE_METADATA_SCHEMA")
        _require(meta["study_id"] == request["study_id"], "SAME_STUDY_REQUIRED")
        _require(meta["timepoint"] == request["timepoint"], "SAME_TIMEPOINT_REQUIRED")
        _require(meta["space"] == request["space"] and meta["transform_version"] == request["transform_version"], "SAME_SPATIAL_CONTEXT_REQUIRED")
        _require(meta == expected["images"][modality]["metadata"], "GENERATED_MODALITY_METADATA_BINDING")
        summaries[modality] = parse_nifti1_generated(item["content"])
    reference = summaries["DWI"]
    for summary in summaries.values():
        _require(summary["shape"] == reference["shape"] and
                 all(abs(a - b) <= 1e-6 for row, other in zip(summary["affine"], reference["affine"]) for a, b in zip(row, other)),
                 "GRID_MISMATCH_NO_SILENT_AFFINE_REWRITE")
    for modality in modalities:
        _require(request["images"][modality]["content"] == expected["images"][modality]["content"], "GENERATOR_EXACT_BYTE_PROVENANCE_MISMATCH")
    input_hash = json_sha({"mode": mode, "generator": generator,
                           "images": {m: {"sha256": request["images"][m]["sha256"], "metadata": request["images"][m]["metadata"]} for m in modalities}})
    return {"schema": "strokeweave-generated-deepisles-input-result-v1", "passed": True,
            "terminal": "STOP", "completed_task": "GENERATED_INPUT_CONTRACT_ONLY_NOT_SEGMENTATION",
            "mode": mode, "modalities": list(modalities), "input_sha256": input_hash,
            "source_commit": SOURCE_COMMIT, "registry_sha256": json_sha(registry),
            "images": summaries, "study_group_semantics": "FIXED_GENERATED_RECIPE_NOT_PATIENT_IDENTITY",
            "coverage_scope": request["coverage_scope"], "biological_registration_proved": False,
            "usable_brain_tissue_or_motion_quality_proved": False, "whole_brain_coverage_proved": False,
            "inference_dispatch_allowed": False, "neural_inference_performed": False,
            "neural_task_completed": False, "ready_for_patient_input": False,
            "new_model_claim": False, "patient_execution": False, "training_enabled": False,
            "labels_sealed": True, "clinical_accuracy_evaluated": False}


def _unverified_input_hash(request):
    """Bind failed attempts to bounded received bytes without retaining values.

    This hash is provenance of rejected input only, not valid medical evidence.
    No path is opened and no untrusted object is stringified or executed.
    """
    hashes = {}
    if type(request) is dict and type(request.get("images")) is dict:
        for modality in ("DWI", "ADC", "FLAIR"):
            item = request["images"].get(modality)
            if type(item) is dict and type(item.get("content")) is bytes and len(item["content"]) <= MAX_BYTES:
                hashes[modality] = sha(item["content"])
    return json_sha({"scope": "REJECTED_INPUT_BYTES_NOT_VERIFIED_EVIDENCE", "bounded_image_hashes": hashes})


def validate_generated_request(request, registry=None):
    """No path/command callback accepted. Failure returns metadata, not values."""
    try:
        registry = load_registry() if registry is None else registry
        report = _validate(request, registry)
        dependency_ids = ["generated_image:" + m + ":" + report["images"][m]["content_sha256"] for m in report["modalities"]]
        evidence = {"source": "DeepISLES_generated_input_adapter", "tool_version": "input_adapter_v1_" + SOURCE_COMMIT,
                    "input_sha256": report["input_sha256"], "output_sha256": json_sha(report),
                    "modality": "+".join(report["modalities"]), "timepoint": request["timepoint"],
                    "space": request["space"], "transform_version": request["transform_version"], "units": "mm",
                    "valid_for": ["generated_input_contract", "future_separately_locked_generated_neural_preflight"],
                    "dependencies": dependency_ids, "observed": True, "adopted": False, "validity": "valid",
                    "handover_requires_dependency_registration_and_current_context_revalidation": True}
    except (InputContractError, KeyError, TypeError, ValueError, struct.error) as exc:
        error_code = str(exc) if isinstance(exc, InputContractError) else "MALFORMED_GENERATED_REQUEST"
        report = {"schema": "strokeweave-generated-deepisles-input-result-v1", "passed": False,
                  "terminal": "REFER", "error_code": error_code, "failure_metadata_only": True,
                  "inference_dispatch_allowed": False, "neural_inference_performed": False,
                  "patient_execution": False, "training_enabled": False, "labels_sealed": True}
        metadata = {"error_code": error_code, "action": "generated_input_contract", "attempt": 1}
        evidence = {"source": "DeepISLES_generated_input_adapter", "tool_version": "input_adapter_v1_" + SOURCE_COMMIT,
                    "input_sha256": _unverified_input_hash(request), "output_sha256": json_sha(metadata),
                    "modality": "UNVERIFIED", "timepoint": "UNVERIFIED", "space": "UNVERIFIED",
                    "transform_version": "UNVERIFIED", "units": "UNVERIFIED", "valid_for": ["technical_failure_metadata_only"],
                    "dependencies": [], "observed": True, "adopted": False, "validity": "invalid",
                    "failure_metadata": metadata, "unverified_payload": None}
    return {"report": report, "evidence_handover": evidence}


def mutation_cases():
    """Frozen controlled faults; no patient files or model outputs are read."""
    cases = []
    for mode, case in (("full_ensemble", "canonical"), ("full_ensemble", "left_handed"),
                       ("full_ensemble", "oblique"), ("SEALS_component", "canonical")):
        cases.append({"name": "valid_" + mode + "_" + case, "request": make_generated_request(mode, case), "expect_pass": True})

    def changed(name, change, code):
        request = make_generated_request()
        change(request)
        cases.append({"name": name, "request": request, "expect_pass": False, "expected_error_code": code})

    def patch(request, offset, format_string, *values):
        item = request["images"]["ADC"]
        content = bytearray(item["content"])
        struct.pack_into(format_string, content, offset, *values)
        item["content"] = bytes(content)
        item["sha256"] = sha(item["content"])

    changed("missing_flair_not_full_ensemble", lambda r: r["images"].pop("FLAIR"), "MODALITY_SET_MISMATCH")
    changed("patient_scope_denied", lambda r: r.update(patient_data=True), "GENERATED_ONLY_REQUIRED")
    changed("different_study", lambda r: r["images"]["ADC"]["metadata"].update(study_id="generated-other-study"), "SAME_STUDY_REQUIRED")
    changed("different_timepoint", lambda r: r["images"]["ADC"]["metadata"].update(timepoint="generated-future"), "SAME_TIMEPOINT_REQUIRED")
    changed("different_transform", lambda r: r["images"]["ADC"]["metadata"].update(transform_version="generated_stale"), "SAME_SPATIAL_CONTEXT_REQUIRED")
    changed("b_value_not_imputed", lambda r: r["images"]["DWI"]["metadata"].update(DWI_b_value_declaration=0), "GENERATED_MODALITY_METADATA_BINDING")
    changed("whole_brain_claim_denied", lambda r: r.update(coverage_scope="whole_brain"), "ACQUIRED_VOLUME_SCOPE_REQUIRED")
    changed("file_path_interface_denied", lambda r: r.update(path="DO_NOT_READ_ANY_PATIENT_FILE"), "EXACT_REQUEST_SCHEMA_NO_PATHS")
    changed("content_hash_corruption", lambda r: r["images"]["ADC"].update(sha256="0" * 64), "CONTENT_HASH_MISMATCH")
    changed("nonfinite_voxel", lambda r: patch(r, 352, "<f", float("nan")), "NONFINITE_VOXEL")
    changed("singular_affine", lambda r: patch(r, 280, "<4f", 0, 0, 0, 0), "SINGULAR_OR_UNBOUNDED_AFFINE")
    changed("different_native_grid", lambda r: patch(r, 292, "<f", -3), "GRID_MISMATCH_NO_SILENT_AFFINE_REWRITE")
    changed("pixdim_affine_conflict", lambda r: patch(r, 80, "<f", 4), "PIXDIM_AFFINE_CONFLICT")
    changed("unknown_or_meter_unit", lambda r: patch(r, 123, "<B", 1), "SPATIAL_MM_NO_TEMPORAL_UNITS_REQUIRED")
    changed("four_dimensional_rejected", lambda r: patch(r, 40, "<h", 4), "STRICT_3D_REQUIRED")
    changed("scaling_not_guessed", lambda r: patch(r, 112, "<f", 2), "NONIDENTITY_OR_UNDEFINED_SCALING_UNSUPPORTED")
    changed("qform_not_silently_selected", lambda r: patch(r, 252, "<h", 1), "SCANNER_SFORM_ONLY_SUBSET_REQUIRED")
    changed("intensity_not_generated", lambda r: patch(r, 352, "<f", 123.5), "GENERATOR_EXACT_BYTE_PROVENANCE_MISMATCH")
    changed("NIfTI2_not_guessed", lambda r: patch(r, 0, "<i", 540), "NIFTI1_LITTLE_ENDIAN_HEADER_REQUIRED")
    return cases
