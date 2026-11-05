"""Constrained generated-task preview, inspired by the earlier owned MVP.

This is a deterministic router, not an LLM, clinical planner or shell agent.
Raw text is not written, returned in reports, or used to grant permissions.
"""

import hashlib
import re


def preview(text):
    if type(text) is not str or not 3 <= len(text) <= 600:
        raise ValueError("Request must contain 3–600 characters")
    lower = text.casefold()
    status, intent, explanation = "NEEDS_CLARIFICATION", "unsupported", "Explicitly request a supported generated task."
    if re.search(r"patient|患者|病人|病例|diagnos|treat|thrombol|thrombectomy|aspirin|治疗|诊断|用药|取栓|溶栓", lower):
        status, intent, explanation = "BLOCKED", "patient_or_clinical", "Patient processing and clinical decisions are not admitted."
    elif re.search(r"[a-z]:[\\/]|/mnt/|https?://|\.nii|\.dcm|\.csv|\.py\b|\b(?:bash|powershell|cmd|exec|sudo)\b|[;`]", lower):
        status, intent, explanation = "BLOCKED", "external_path_or_command", "No external file, URL, upload or executable command interface exists."
    elif re.search(r"ignore|override|unseal|unlock|relax|cal/hold|test labels|绕过|忽略|解封|放宽", lower):
        status, intent, explanation = "BLOCKED", "guard_override", "A task request cannot alter admission, labels or risk rules."
    elif "deepisles" in lower or "synthstroke" in lower:
        status, intent, explanation = "BLOCKED", "external_model_not_bundled", "External medical models require separate licensing, runtime qualification and data admission. This demo does not load them."
    elif re.search(r"generated|synthetic|demo|phantom|生成|合成|演示", lower):
        if re.search(r"compare|policy|policies|voi|策略|比较", lower):
            status, intent, explanation = "READY", "compare", "Preview a shared-policy comparison on the declared generated witness."
        elif re.search(r"nifti|contract|input guard|输入|契约", lower):
            status, intent, explanation = "READY", "input-check", "Preview a fixed generated NIfTI input contract, not model inference."
        elif re.search(r"volume|geometry|repair|mask|体积|空间|修复|掩膜", lower):
            status, intent, explanation = "READY", "demo", "Preview the bounded generated native-space workflow."
    return {"status": status, "intent": intent, "explanation": explanation,
            "request_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "execution_triggered": False, "patient_execution": False,
            "engine": "constrained_local_router_not_LLM"}
