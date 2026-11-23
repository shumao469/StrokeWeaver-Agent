"""Case-bound planning and review for the synthetic handoff workbench."""

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re


KINDS = {
    "imaging": "Imaging report",
    "medications": "Medication record",
    "rehab": "Rehabilitation plan",
    "follow_up": "Follow-up plan",
}
TOPIC_WORDS = {
    "imaging": ("影像", "影象", "磁共振", "报告", "mri", "imaging", "image", "scan", "radiology", "report"),
    "medications": ("用药", "药物", "药品", "药单", "medication", "medicine", "medications", "medicines", "drug"),
    "rehab": ("康复", "训练", "rehab", "rehabilitation"),
    "follow_up": ("随访", "复诊", "预约", "门诊", "follow-up", "follow up", "followup", "appointment", "visit"),
}
CONTEXT_WORDS = ("它", "这个", "这项", "来源", "出处", "原文", "哪份", "时间", "何时", "几点", "什么时候", "when", "source", "its", "that", "original", "where")
NEW_CONCERN_WORDS = (
    "突然", "新出现", "新发", "加重", "急诊", "紧急", "晕倒", "胸痛", "麻木", "无力", "嘴歪",
    "说不清", "眩晕", "头痛", "出血", "停药", "换药", "改药", "调药", "剂量", "加量", "减量",
    "漏服", "补服", "副作用", "怎么办", "能吃吗", "要吃吗", "该不该", "可以吃", "是否吃",
    "emergency", "dose", "symptom", "stop taking", "side effect", "sudden", "worsening", "new weakness", "new numbness", "missed dose", "change my medication", "shortness of breath", "chest pain",
)
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def digest(value):
    body = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    return sha256(body.encode("utf-8")).hexdigest()


def _time(value):
    if not isinstance(value, str):
        raise ValueError("Invalid record timestamp.")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.utcoffset() != timezone.utc.utcoffset(stamp):
        raise ValueError("Case and record timestamps must use UTC.")
    return stamp


def load_demo_cases():
    data = json.loads((FIXTURES / "demo_cases.json").read_text(encoding="utf-8"))
    for case in data:
        Episode(case)
    return data


class Episode:
    """A synthetic episode. Each state transition is bound to one case snapshot."""

    def __init__(self, case):
        self.case_id = case["case_id"]
        if not isinstance(self.case_id, str) or not self.case_id.startswith("SYN-") or not ID.fullmatch(self.case_id):
            raise ValueError("Only registered synthetic cases are accepted.")
        self.title = case["title"]
        self.as_of = case["as_of"]
        _time(self.as_of)
        self.required_kinds = tuple(case["required_kinds"])
        if (
            not self.required_kinds
            or len(self.required_kinds) != len(set(self.required_kinds))
            or any(kind not in KINDS for kind in self.required_kinds)
            or type(case["handoff_confirmed"]) is not bool
        ):
            raise ValueError("Invalid case requirements or handoff status.")
        self.handoff_confirmed = case["handoff_confirmed"]
        self._records = self._validate_records(case["records"])
        self._update = deepcopy(case.get("update"))
        if self._update is not None:
            self._validate_records([*self._records.values(), self._update])
            if _time(self._update["recorded_at"]) <= _time(self.as_of):
                raise ValueError("A simulated update must follow the current case timestamp.")
        self._resolutions = {}
        self._plan = None
        self._referrals = []
        self._topics = {}
        self._events = []
        self._log("EPISODE_LOADED", snapshot_sha256=self._snapshot())

    @staticmethod
    def _validate_records(records):
        by_id = {}
        for item in records:
            record_id = item["id"]
            if (
                not isinstance(record_id, str)
                or not ID.fullmatch(record_id)
                or record_id in by_id
                or item["kind"] not in KINDS
                or type(item["version"]) is not int
                or item["version"] < 1
                or not isinstance(item["text"], str)
                or not item["text"].strip()
            ):
                raise ValueError("Invalid source identifier, type, or version.")
            _time(item["recorded_at"])
            by_id[record_id] = {key: item[key] for key in ("id", "kind", "version", "recorded_at", "text")}
            by_id[record_id]["supersedes"] = item.get("supersedes")
        for row in by_id.values():
            parent = row["supersedes"]
            if parent is None:
                continue
            if not isinstance(parent, str) or parent not in by_id:
                raise ValueError("The superseded source record does not exist.")
            prior = by_id[parent]
            if (
                prior["kind"] != row["kind"]
                or prior["version"] >= row["version"]
                or _time(prior["recorded_at"]) >= _time(row["recorded_at"])
            ):
                raise ValueError("Superseding records must share a category and refer to an earlier version.")
        return by_id

    @property
    def can_update(self):
        return self._update is not None

    def _timeline(self):
        bound = _time(self.as_of)
        return sorted(
            (row for row in self._records.values() if _time(row["recorded_at"]) <= bound),
            key=lambda row: (_time(row["recorded_at"]), row["id"]),
        )

    def _snapshot(self):
        return digest({
            "case_id": self.case_id,
            "as_of": self.as_of,
            "required_kinds": self.required_kinds,
            "handoff_confirmed": self.handoff_confirmed,
            "available_records": self._timeline(),
            "resolutions": self._resolutions,
        })

    def _heads(self):
        timeline = self._timeline()
        replaced = {row["supersedes"] for row in timeline}
        return {kind: [row for row in timeline if row["kind"] == kind and row["id"] not in replaced] for kind in KINDS}

    def _current_and_issues(self):
        current, issues = [], []
        for kind, candidates in self._heads().items():
            chosen = self._resolutions.get(kind)
            selected = [row for row in candidates if row["id"] == chosen]
            if selected or len(candidates) == 1:
                current.append((selected or candidates)[0])
            elif candidates:
                issues.append(self._issue("CONFLICT", kind, candidates))
            elif kind in self.required_kinds:
                issues.append(self._issue("MISSING", kind))
        if not self.handoff_confirmed:
            issues.append(self._issue("HANDOFF_PENDING", "handoff"))
        return current, issues

    @staticmethod
    def _issue(code, kind, records=()):
        return {
            "id": f"{code}:{kind}",
            "code": code,
            "kind": kind,
            "record_ids": [row["id"] for row in records],
        }

    def _plan_status(self, snapshot, issues):
        if self._plan:
            return "SIGNED" if self._plan["snapshot_sha256"] == snapshot and not issues else "STALE"
        return "NEEDS_REVIEW" if issues else "DRAFT"

    def state(self):
        current, issues = self._current_and_issues()
        snapshot = self._snapshot()
        return deepcopy({
            "current": current,
            "timeline": self._timeline(),
            "issues": issues,
            "plan_status": self._plan_status(snapshot, issues),
            "plan": self._plan,
            "referrals": self._referrals,
            "snapshot_sha256": snapshot,
        })

    def patient_state(self):
        current = self.state()
        plan = current["plan"] if current["plan_status"] == "SIGNED" else None
        return {"plan_status": current["plan_status"], "plan": plan}

    def _log(self, event, **fields):
        entry = {
            "sequence": len(self._events) + 1,
            "previous_sha256": self._events[-1]["event_sha256"] if self._events else "0" * 64,
            "case_id": self.case_id,
            "as_of": self.as_of,
            "event": event,
            **fields,
        }
        self._events.append({**entry, "event_sha256": digest(entry)})

    def _check_snapshot(self, expected):
        if expected != self._snapshot():
            raise ValueError("Case evidence has changed. Review the current records again.")

    def approve(self, expected_sha256):
        self._check_snapshot(expected_sha256)
        current, issues = self._current_and_issues()
        if issues:
            raise ValueError("Resolve the pending review items before signing.")
        if self._plan is not None and self._plan["snapshot_sha256"] == expected_sha256:
            return deepcopy(self._plan)
        plan = {
            "snapshot_sha256": expected_sha256,
            "signed_at": self.as_of,
            "sections": [{"kind": row["kind"], "text": row["text"], "source_id": row["id"]} for row in current],
        }
        self._plan = {**plan, "plan_id": f"{self.case_id}-PLAN-{digest(plan)[:12]}"}
        self._topics.pop("patient", None)
        self._log("PLAN_SIGNED", plan_id=self._plan["plan_id"], snapshot_sha256=expected_sha256)
        return deepcopy(self._plan)

    def apply_update(self):
        if self._update is None:
            raise ValueError("This case has no pending synthetic update.")
        update = self._update
        validated = self._validate_records([*self._records.values(), update])
        previous_heads = self._heads()
        previous_status = self.state()["plan_status"]
        self._records = validated
        self.as_of = update["recorded_at"]
        for kind, previous in previous_heads.items():
            if previous != self._heads()[kind]:
                self._resolutions.pop(kind, None)
        self._update = None
        self._topics.pop("patient", None)
        self._log("RECORD_UPDATED", record_id=update["id"], version=update["version"], snapshot_sha256=self._snapshot())
        if previous_status == "SIGNED":
            self._log("PLAN_REVIEW_REQUIRED", plan_id=self._plan["plan_id"], snapshot_sha256=self._snapshot())

    def acknowledge_handoff(self):
        if not self.handoff_confirmed:
            self.handoff_confirmed = True
            self._log("HANDOFF_CONFIRMED", snapshot_sha256=self._snapshot())

    def resolve_conflict(self, kind, record_id, expected_sha256):
        self._check_snapshot(expected_sha256)
        heads = self._heads().get(kind, [])
        if len(heads) < 2 or record_id not in {record["id"] for record in heads}:
            raise ValueError("Choose one of the conflicting source records.")
        if self._resolutions.get(kind) != record_id:
            self._resolutions[kind] = record_id
            self._log("SOURCE_CONFIRMED", kind=kind, source_id=record_id, snapshot_sha256=self._snapshot())

    def acknowledge_referral(self, referral_id):
        item = next((entry for entry in self._referrals if entry["id"] == referral_id), None)
        if item is None:
            raise ValueError("Referral not found.")
        if item["status"] == "PENDING":
            item["status"] = "ACKNOWLEDGED"
            self._log("REFERRAL_ACKNOWLEDGED", referral_id=referral_id)

    def _refer(self, reason, message, topics):
        snapshot = self._snapshot()
        key = digest([snapshot, reason, topics])[:12]
        referral_id = f"{self.case_id}-REV-{key}"
        if all(row["id"] != referral_id for row in self._referrals):
            self._referrals.append({
                "id": referral_id,
                "status": "PENDING",
                "message": message,
                "reason": reason,
                "snapshot_sha256": snapshot,
            })
            self._log("REFERRAL_QUEUED", referral_id=referral_id, reason=reason, snapshot_sha256=snapshot)
        return message

    def _reply(self, role, action, text, citations=()):
        self._log("CHAT_ROUTED", role=role, action=action, source_ids=list(citations))
        return {"text": text, "citations": list(citations), "action": action}

    def chat(self, role, message):
        if role not in {"doctor", "patient"} or not isinstance(message, str) or not 0 < len(message.strip()) <= 1000:
            raise ValueError("Choose a role and enter a synthetic case question of 1–1000 characters.")
        query = message.strip().casefold()
        requested = tuple(kind for kind, words in TOPIC_WORDS.items() if any(word in query for word in words))
        if role == "patient" and any(word in query for word in NEW_CONCERN_WORDS):
            message = self._refer(
                "CLINICAL_QUESTION", "This question requires a clinician and has been added to the demonstration review queue. For real health concerns, contact a healthcare professional.", requested
            )
            return self._reply(role, "REFER", message)
        if not requested and any(word in query for word in CONTEXT_WORDS):
            requested = self._topics.get(role, ())
        view = self.state()
        if role == "patient":
            if view["plan_status"] != "SIGNED":
                message = self._refer(
                    "PLAN_UNAVAILABLE", "No signed plan is available. This request has been added to the demonstration review queue.", requested
                )
                return self._reply(role, "REFER", message)
            general = any(word in query for word in ("我的计划", "出院计划", "全部安排", "计划摘要", "plan"))
            if not requested and not general:
                return self._reply(role, "CLARIFY", "Ask about an approved imaging, medication, rehabilitation, or follow-up item.")
            rows = [row for row in view["plan"]["sections"] if not requested or row["kind"] in requested]
            if not rows or (requested and {row["kind"] for row in rows} != set(requested)):
                message = self._refer("TOPIC_NOT_SIGNED", "The signed plan does not contain this item. It has been added to the demonstration review queue.", requested)
                return self._reply(role, "REFER", message)
            self._topics[role] = tuple(row["kind"] for row in rows)
            return self._reply(role, "ANSWER", "\n".join(f"{KINDS[row['kind']]}: {row['text']}" for row in rows),
                               [row["source_id"] for row in rows])
        if not requested and not any(word in query for word in (
            "交接", "出院", "清单", "汇总", "摘要", "冲突", "缺失", "待办", "复核", "timeline", "summary", "checklist", "handoff", "discharge", "review", "conflict", "missing", "status", "summarize"
        )):
            return self._reply(role, "CLARIFY", "Ask for the handoff summary or select imaging, medication, rehabilitation, or follow-up.")
        rows = [row for row in view["current"] if not requested or row["kind"] in requested]
        issues = [item for item in view["issues"] if not requested or item["kind"] in (*requested, "handoff")]
        self._topics[role] = requested or tuple(row["kind"] for row in rows)
        lines = [f"{KINDS[row['kind']]} · version {row['version']} ({row['recorded_at']}): {row['text']}" for row in rows]
        explanations = {"MISSING": "Missing record", "CONFLICT": "Unresolved source conflict", "HANDOFF_PENDING": "Handoff is not confirmed"}
        lines.extend(f"Review · {KINDS.get(issue['kind'], 'Handoff')}: {explanations[issue['code']]}" for issue in issues)
        ids = [row["id"] for row in rows]
        ids.extend(record_id for issue in issues for record_id in issue["record_ids"])
        return self._reply(role, "REVIEW" if issues else "ANSWER",
                           "\n".join(lines) or "No record for this category is available at the current time.", ids)

    def export_audit(self):
        scope = {
            "schema": "strokeweaver-synthetic-handoff-audit-v1",
            "generated_only": True,
            "case_id": self.case_id,
            "snapshot_sha256": self._snapshot(),
            "events": deepcopy(self._events),
        }
        return {**scope, "audit_sha256": digest(scope)}


def verify_audit(receipt):
    if not isinstance(receipt, dict) or receipt.get("generated_only") is not True:
        return False
    head = "0" * 64
    try:
        if not receipt["events"]:
            return False
        for i, row in enumerate(receipt["events"], 1):
            if (row["sequence"] != i or row["case_id"] != receipt["case_id"] or row["previous_sha256"] != head):
                return False
            head = row["event_sha256"]
            if head != digest({key: value for key, value in row.items() if key != "event_sha256"}):
                return False
        return receipt["audit_sha256"] == digest({key: value for key, value in receipt.items() if key != "audit_sha256"})
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
