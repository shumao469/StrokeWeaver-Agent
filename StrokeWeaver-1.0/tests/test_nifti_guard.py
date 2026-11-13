"""Generated in-memory unit tests; no model, patient file or GPU calls."""

import copy
import math
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from strokeweaver_agent.nifti_guard import (
    CASES, InputContractError, MAX_BYTES, SOURCE_COMMIT, geometry_contract,
    json_sha, load_registry, make_generated_nifti, make_generated_request,
    mutation_cases, parse_nifti1_generated, sha, validate_generated_request,
)


class InputAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()

    def mutate(self, offset, fmt, *values):
        data = bytearray(make_generated_nifti("DWI"))
        struct.pack_into(fmt, data, offset, *values)
        return bytes(data)

    def test_real_nifti_header_and_payload(self):
        data = make_generated_nifti("DWI")
        self.assertEqual(struct.unpack_from("<i", data, 0)[0], 348)
        self.assertEqual(data[344:348], b"n+1\0")
        result = parse_nifti1_generated(data)
        self.assertEqual(result["shape"], [4, 3, 2])
        self.assertEqual(result["voxel_count"], 24)
        self.assertEqual(result["finite_voxel_count"], 24)
        self.assertEqual(result["content_bytes"], 448)
        self.assertEqual(result["voxel_volume_mm3"], 15)

    def test_deterministic_recipe_distinct_modalities(self):
        self.assertEqual(make_generated_nifti("DWI"), make_generated_nifti("DWI"))
        self.assertEqual(len({sha(make_generated_nifti(m)) for m in ("DWI", "ADC", "FLAIR")}), 3)

    def test_all_generated_affines_invert(self):
        for case in CASES:
            result = parse_nifti1_generated(make_generated_nifti("DWI", case))
            self.assertLessEqual(result["coordinate_roundtrip_max_abs_voxel_error"], 1e-6)
            self.assertFalse(result["biological_registration_proved"])
            self.assertFalse(result["whole_brain_coverage_proved"])

    def test_left_handed_is_not_corrupt(self):
        result = parse_nifti1_generated(make_generated_nifti("DWI", "left_handed"))
        self.assertLess(result["determinant_mm3"], 0)
        self.assertEqual(result["voxel_volume_mm3"], 15)

    def test_full_three_modality_and_component_distinguished(self):
        full = validate_generated_request(make_generated_request(), self.registry)["report"]
        single = validate_generated_request(make_generated_request("SEALS_component"), self.registry)["report"]
        self.assertTrue(full["passed"] and single["passed"])
        self.assertEqual(full["modalities"], ["DWI", "ADC", "FLAIR"])
        self.assertEqual(single["modalities"], ["DWI", "ADC"])
        self.assertFalse(full["neural_task_completed"])
        self.assertFalse(single["inference_dispatch_allowed"])

    def test_all_declared_positive_and_negative_cases(self):
        for case in mutation_cases():
            with self.subTest(name=case["name"]):
                result = validate_generated_request(case["request"], self.registry)
                self.assertEqual(result["report"]["passed"], case["expect_pass"])
                if not case["expect_pass"]:
                    self.assertEqual(result["report"]["error_code"], case["expected_error_code"])

    def test_invalid_outputs_only_failure_metadata(self):
        request = make_generated_request()
        request["images"]["ADC"]["sha256"] = "0" * 64
        result = validate_generated_request(request, self.registry)
        self.assertEqual(result["report"]["terminal"], "REFER")
        self.assertNotIn("images", result["report"])
        evidence = result["evidence_handover"]
        self.assertIsNone(evidence["unverified_payload"])
        self.assertEqual(evidence["validity"], "invalid")
        self.assertFalse(evidence["adopted"])
        self.assertEqual(evidence["output_sha256"], json_sha(evidence["failure_metadata"]))

    def test_handover_observed_not_adopted_and_hash_bound(self):
        result = validate_generated_request(make_generated_request(), self.registry)
        report, evidence = result["report"], result["evidence_handover"]
        self.assertTrue(evidence["observed"])
        self.assertFalse(evidence["adopted"])
        self.assertEqual(evidence["output_sha256"], json_sha(report))
        self.assertEqual(len(evidence["dependencies"]), 3)
        self.assertTrue(evidence["handover_requires_dependency_registration_and_current_context_revalidation"])

    def test_no_path_interface(self):
        with self.assertRaisesRegex(InputContractError, "BYTES_ONLY"):
            parse_nifti1_generated("DO_NOT_OPEN")
        request = make_generated_request()
        request["images"]["DWI"]["path"] = "DO_NOT_OPEN"
        self.assertEqual(validate_generated_request(request, self.registry)["report"]["error_code"], "EXACT_IMAGE_SCHEMA_NO_PATHS")

    def test_finite_voxels_required(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaisesRegex(InputContractError, "NONFINITE_VOXEL"):
                parse_nifti1_generated(self.mutate(352, "<f", value))

    def test_no_undefined_nibabel_slope_guessing(self):
        with self.assertRaisesRegex(InputContractError, "SCALING_UNSUPPORTED"):
            parse_nifti1_generated(self.mutate(112, "<f", float("nan")))

    def test_big_endian_and_nifti2_not_guessed(self):
        for fmt, value in ((">i", 348), ("<i", 540)):
            with self.assertRaisesRegex(InputContractError, "NIFTI1_LITTLE_ENDIAN"):
                parse_nifti1_generated(self.mutate(0, fmt, value))

    def test_payload_truncation_or_trailing_not_ignored(self):
        data = make_generated_nifti("DWI")
        for changed in (data[:-1], data + b"\0"):
            with self.assertRaisesRegex(InputContractError, "PAYLOAD_LENGTH"):
                parse_nifti1_generated(changed)

    def test_dimensions_and_byte_resource_cap(self):
        for length in (-1, 0, 65, 32767):
            with self.assertRaisesRegex(InputContractError, "DIMENSION_BOUNDS"):
                parse_nifti1_generated(self.mutate(42, "<h", length))
        with self.assertRaisesRegex(InputContractError, "BOUNDED_NIFTI_LENGTH"):
            parse_nifti1_generated(b"\0" * (MAX_BYTES + 1))

    def test_singular_and_nonfinite_affine(self):
        for value in (0, float("nan"), float("inf")):
            with self.assertRaises(InputContractError):
                parse_nifti1_generated(self.mutate(280, "<f", value))

    def test_unused_nonfinite_header_not_ignored(self):
        with self.assertRaisesRegex(InputContractError, "UNUSED_HEADER"):
            parse_nifti1_generated(self.mutate(124, "<f", float("nan")))

    def test_nifti_not_general_dicom_or_compression(self):
        data = bytearray(make_generated_nifti("DWI"))
        data[:2] = b"\x1f\x8b"
        with self.assertRaisesRegex(InputContractError, "COMPRESSED"):
            parse_nifti1_generated(bytes(data))

    def test_ct_or_t1_never_routes_to_deepisles(self):
        for modality in ("CT", "T1"):
            with self.assertRaisesRegex(InputContractError, "UNSUPPORTED_MODALITY"):
                make_generated_nifti(modality)

    def test_registry_scope_never_enables_models(self):
        registry = copy.deepcopy(self.registry)
        registry["inference_dispatch_allowed"] = True
        self.assertFalse(validate_generated_request(make_generated_request(), registry)["report"]["passed"])
        self.assertEqual(self.registry["upstream_commit"], SOURCE_COMMIT)
        self.assertTrue(self.registry["training_exposure"]["ISLES22_exposed"])
        self.assertFalse(self.registry["training_exposure"]["unseen_tool_on_ISLES_claim_allowed"])

    def test_flags_alone_cannot_authorize_patient_bytes(self):
        request = make_generated_request()
        content = bytearray(request["images"]["DWI"]["content"])
        struct.pack_into("<f", content, 352, 9999)
        request["images"]["DWI"].update(content=bytes(content), sha256=sha(content))
        result = validate_generated_request(request, self.registry)
        self.assertEqual(result["report"]["error_code"], "GENERATOR_EXACT_BYTE_PROVENANCE_MISMATCH")

    def test_failed_attempt_hash_still_binds_received_bytes(self):
        first = make_generated_request()
        first["images"]["DWI"]["sha256"] = "0" * 64
        second = copy.deepcopy(first)
        content = bytearray(second["images"]["DWI"]["content"])
        struct.pack_into("<f", content, 352, 999)
        second["images"]["DWI"]["content"] = bytes(content)
        left = validate_generated_request(first, self.registry)
        right = validate_generated_request(second, self.registry)
        self.assertNotEqual(left["evidence_handover"]["input_sha256"], right["evidence_handover"]["input_sha256"])
        self.assertTrue(left["report"]["failure_metadata_only"])
        self.assertIsNone(left["evidence_handover"]["unverified_payload"])


if __name__ == "__main__":
    unittest.main()
