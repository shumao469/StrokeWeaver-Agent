"""Regression checks use fresh fabricated records and never patient data."""

from copy import deepcopy
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "StrokeWeaver-3.0"))
from sw3_phase2.core import Episode, verify_audit
from sw3_phase2.followup.chat import ContractModel, ModelUnavailable
from sw3_phase2.followup.release.scope import WorkbenchNavigationPolicy


def fixture():
    records = [
        {"id": "SYN-CHATNEW-imaging-1", "kind": "imaging", "version": 1,
         "recorded_at": "2026-03-01T09:00:00Z", "text": "An imaging record was archived for this exercise."},
        {"id": "SYN-CHATNEW-medications-1", "kind": "medications", "version": 1,
         "recorded_at": "2026-03-02T09:00:00Z", "text": "A medication list was filed for this exercise."},
        {"id": "SYN-CHATNEW-rehab-1", "kind": "rehab", "version": 1,
         "recorded_at": "2026-03-03T09:00:00Z", "text": "A rehabilitation note was filed for this exercise."},
        {"id": "SYN-CHATNEW-followup-1", "kind": "follow_up", "version": 1,
         "recorded_at": "2026-03-04T09:00:00Z", "text": "A follow-up note was filed for this exercise."},
    ]
    return {"case_id": "SYN-CHATNEW-01", "title": "Synthetic exercise", "as_of": "2026-03-05T12:00:00Z",
            "required_kinds": ["imaging", "medications", "rehab", "follow_up"], "handoff_confirmed": True,
            "records": records,
            "update": {"id": "SYN-CHATNEW-imaging-2", "kind": "imaging", "version": 2,
                       "recorded_at": "2026-03-06T09:00:00Z", "text": "An updated imaging record was archived.",
                       "supersedes": "SYN-CHATNEW-imaging-1"}}


class OfflineModel:
    def choose(self, **kwargs):
        raise ModelUnavailable("local_files_not_configured")


class InvalidModel:
    def choose(self, **kwargs):
        return {"tool": "approve", "record_id": "unsafe"}


class StatusFirstModel(ContractModel):
    def choose(self, **kwargs):
        if "review_status" in kwargs["calls"]:
            return {"tool": "review_status", "record_id": ""}
        return super().choose(**kwargs)


class IntentModel(ContractModel):
    def choose(self, **kwargs):
        if kwargs["context"].get("mode") == "route_intent":
            name = "route_imaging" if "radiographer" in kwargs["context"]["question"] else "route_clarify"
            return {"tool": name, "record_id": ""}
        return super().choose(**kwargs)


class LastRecordModel(ContractModel):
    def choose(self, **kwargs):
        if kwargs["ids"]:
            return {"tool": "inspect_record", "record_id": kwargs["ids"][-1]}
        return super().choose(**kwargs)


class UpdateDuringCall:
    def __init__(self, fail):
        self.policy = None
        self.fail = fail

    def choose(self, **kwargs):
        self.policy.apply_update()
        if self.fail:
            raise ModelUnavailable("local_files_not_configured")
        return {"tool": kwargs["calls"][0], "record_id": ""}


class V3Intents(unittest.TestCase):
    def policy(self, model=None, case=None):
        return WorkbenchNavigationPolicy("strokeweaver", deepcopy(case or fixture()), model or ContractModel())

    def test_combined_questions_keep_both_categories(self):
        policy = self.policy()
        result = policy.chat("doctor", "Summarize the medication and physical therapy records.")
        self.assertEqual(set(result["citations"]), {"SYN-CHATNEW-medications-1", "SYN-CHATNEW-rehab-1"})
        self.assertEqual(result["model_calls"], 0)
        policy.approve(policy.state()["snapshot_sha256"])
        patient = policy.chat("patient", "Show my medication and rehabilitation plan.")
        self.assertEqual(set(patient["citations"]), {"SYN-CHATNEW-medications-1", "SYN-CHATNEW-rehab-1"})

    def test_context_timestamp_and_source_are_grounded(self):
        for model in (ContractModel(), StatusFirstModel(), OfflineModel()):
            policy = self.policy(model)
            first = policy.chat("doctor", "Find the current MRI source.")
            second = policy.chat("doctor", "When was it recorded?")
            self.assertEqual(first["citations"], ["SYN-CHATNEW-imaging-1"])
            self.assertEqual(second["citations"], first["citations"])
            self.assertIn("2026-03-01T09:00:00Z", second["text"])
        policy.approve(policy.state()["snapshot_sha256"])
        policy.chat("patient", "Show my imaging plan")
        timed = policy.chat("patient", "When was it recorded?")
        self.assertEqual(timed["citations"], ["SYN-CHATNEW-imaging-1"])
        self.assertIn("2026-03-01T09:00:00Z", timed["text"])
        self.assertTrue(verify_audit(policy.export_audit()))

    def test_history_and_date_never_invent_an_unavailable_record(self):
        policy = self.policy(OfflineModel())
        dated = policy.chat("doctor", "Find the imaging source recorded on 2026-03-01.")
        self.assertEqual(dated["citations"], ["SYN-CHATNEW-imaging-1"])
        missing = policy.chat("doctor", "Find the MRI source from 2027-01-01.")
        self.assertEqual((missing["action"], missing["citations"]), ("CLARIFY", []))
        unknown = policy.chat("doctor", "Find SYN-NOT-A-REAL-RECORD.")
        self.assertEqual((unknown["action"], unknown["citations"]), ("CLARIFY", []))
        policy.apply_update()
        changes = policy.chat("doctor", "What changed in the MRI?")
        self.assertEqual(changes["citations"], ["SYN-CHATNEW-imaging-1", "SYN-CHATNEW-imaging-2"])
        self.assertIn("An updated imaging record was archived.", changes["text"])
        self.assertNotIn("2027-01-01", changes["text"])

    def test_patient_gates_apply_across_turns_and_model_failures(self):
        for model in (OfflineModel(), InvalidModel(), ContractModel()):
            policy = self.policy(model)
            self.assertEqual(policy.chat("patient", "Show my plan")["action"], "REFER")
            policy.approve(policy.state()["snapshot_sha256"])
            self.assertEqual(policy.chat("patient", "Is this safe for me?")["action"], "REFER")
            self.assertEqual(policy.chat("patient", "Please email the plan to my family")["action"], "REFER")
            self.assertEqual(policy.chat("patient", "Show my imaging and follow-up plan")["action"], "ANSWER")
            policy.apply_update()
            self.assertEqual(policy.chat("patient", "Show my plan")["action"], "REFER")

    def test_patient_medical_decisions_are_referred_without_plan_content(self):
        questions = (
            "I am allergic to this medication, can I use it?",
            "Can I skip my medication tomorrow?",
            "I have a severe headache, can the medication help?",
            "I cannot feel my arm after taking medication.",
            "I feel dizzy after my medicine.",
        )
        policy = self.policy()
        policy.approve(policy.state()["snapshot_sha256"])
        for question in questions:
            reply = policy.chat("patient", question)
            self.assertEqual((reply["action"], reply["citations"], reply["model_calls"]), ("REFER", [], 0))
            self.assertNotIn("A medication list was filed", reply["text"])
        approved = policy.chat("patient", "Show my medication plan")
        self.assertEqual((approved["action"], approved["citations"]), ("ANSWER", ["SYN-CHATNEW-medications-1"]))

    def test_similar_but_nonexistent_source_identifier_is_not_matched(self):
        policy = self.policy()
        for question in ("Find SYN-CHATNEW-imaging-1-NOT-EXIST", "Find SYN-CHATNEW-imaging-1x",
                         "Find SYN-CHATNEW-imaging-1 and SYN-CHATNEW-unknown-9"):
            reply = policy.chat("doctor", question)
            self.assertEqual((reply["action"], reply["citations"]), ("CLARIFY", []))
        found = policy.chat("doctor", "Find SYN-CHATNEW-imaging-1.")
        self.assertEqual(found["citations"], ["SYN-CHATNEW-imaging-1"])

    def test_existing_non_syn_prefixed_source_identifiers_remain_supported(self):
        case = fixture()
        case["records"][0]["id"] = "LEGACY.report_1"
        case["update"]["supersedes"] = "LEGACY.report_1"
        policy = self.policy(case=case)
        found = policy.chat("doctor", "Find LEGACY.report_1.")
        self.assertEqual(found["citations"], ["LEGACY.report_1"])
        unknown = policy.chat("doctor", "Find LEGACY.report_1-ghost")
        self.assertEqual((unknown["action"], unknown["citations"]), ("CLARIFY", []))

    def test_update_during_model_call_never_releases_old_plan(self):
        for fail in (True, False):
            model = UpdateDuringCall(fail)
            policy = self.policy(model)
            model.policy = policy
            policy.approve(policy.state()["snapshot_sha256"])
            reply = policy.chat("patient", "Show my imaging plan")
            self.assertEqual(policy.state()["plan_status"], "STALE")
            self.assertEqual((reply["action"], reply["citations"]), ("REFER", []))
            self.assertEqual(reply["failure"], "context_changed_before_tool")
            self.assertNotIn("An imaging record was archived", reply["text"])

    def test_update_during_intent_routing_forces_fresh_evidence(self):
        model = UpdateDuringCall(True)
        policy = self.policy(model)
        model.policy = policy
        reply = policy.chat("doctor", "What did the radiographer document?")
        self.assertEqual(reply["failure"], "context_changed_before_tool")
        self.assertEqual((reply["action"], reply["citations"]), ("CLARIFY", []))
        self.assertEqual(policy.state()["timeline"][-1]["id"], "SYN-CHATNEW-imaging-2")

    def test_concurrent_external_update_is_serialized_with_chat(self):
        entered = threading.Event()
        release = threading.Event()
        updated = threading.Event()

        class BlockingModel:
            def choose(self, **kwargs):
                entered.set()
                if not release.wait(5):
                    raise ModelUnavailable("timeout")
                return {"tool": "open_signed_plan", "record_id": ""}

        policy = self.policy(BlockingModel())
        policy.approve(policy.state()["snapshot_sha256"])
        replies = []
        chat_thread = threading.Thread(target=lambda: replies.append(policy.chat("patient", "Show my imaging plan")))

        def update():
            policy.apply_update()
            updated.set()

        update_thread = threading.Thread(target=update)
        chat_thread.start()
        self.assertTrue(entered.wait(2))
        update_thread.start()
        self.assertFalse(updated.wait(0.1))
        release.set()
        chat_thread.join(5)
        update_thread.join(5)
        self.assertFalse(chat_thread.is_alive())
        self.assertTrue(updated.is_set())
        self.assertEqual(replies[0]["action"], "ANSWER")
        self.assertEqual(policy.chat("patient", "Show my imaging plan")["action"], "REFER")

    def test_multiple_ambiguous_records_require_specific_selection(self):
        case = fixture()
        extra = dict(case["records"][0], id="SYN-CHATNEW-imaging-other")
        case["records"].append(extra)
        policy = self.policy(ContractModel(), case)
        result = policy.chat("doctor", "Find the current imaging source.")
        self.assertEqual((result["action"], result["citations"]), ("REVIEW", []))
        ambiguous = policy.chat("doctor", "Find the MRI source from 2026-03-01.")
        self.assertEqual((ambiguous["action"], ambiguous["citations"]), ("CLARIFY", []))

    def test_requested_category_limits_model_source_selection(self):
        policy = self.policy(LastRecordModel())
        result = policy.chat("doctor", "Find the MRI source.")
        self.assertEqual(result["citations"], ["SYN-CHATNEW-imaging-1"])

    def test_constrained_intent_routes_only_to_grounded_records(self):
        policy = self.policy(IntentModel())
        response = policy.chat("doctor", "What did the radiographer document?")
        self.assertEqual(response["citations"], ["SYN-CHATNEW-imaging-1"])
        self.assertEqual(response["tool_trace"][0]["tool"], "route_imaging")
        self.assertIn("An imaging record was archived for this exercise.", response["text"])
        unrelated = policy.chat("doctor", "Tell me a joke.")
        self.assertEqual((unrelated["action"], unrelated["citations"], unrelated["model_calls"]), ("CLARIFY", [], 0))
        combined = policy.chat("doctor", "What did the radiographer and pharmacist document?")
        self.assertEqual(set(combined["citations"]), {"SYN-CHATNEW-imaging-1", "SYN-CHATNEW-medications-1"})
        offline = self.policy(OfflineModel()).chat("doctor", "What did the radiographer document?")
        self.assertEqual((offline["action"], offline["citations"]), ("CLARIFY", []))


if __name__ == "__main__":
    unittest.main()
