"""Route requests to change or distribute a signed plan to human review."""

import re

from sw3_phase2.followup.chat import NavigationPolicy


_CHANGE_PLAN = re.compile(
    r"(?:更改|修改|帮我改|替我改|改到|改签|调整|重排|延期|提前|取消|作废|重新安排)"
    r"[^。！？]{0,18}(?:预约|随访|复诊|挂号|交接|签署|计划|康复|用药)"
    r"|(?:预约|随访|复诊|挂号)[^。！？]{0,14}(?:改到|换到|换成|推迟|取消)"
    r"|\b(?:reschedule|cancel|modify|change)\b[^.!?]{0,36}\b(?:appointment|visit|follow.up|plan)\b",
    re.IGNORECASE,
)
_SHARE = re.compile(
    r"(?:发到|发去|发至|发往|传到|传给|贴到|上传|共享|群发|发给|给群里)"
    r"[^。！？]{0,15}(?:群|外部|私人|朋友圈|网站|邮箱|链接|同事)"
    r"|\b(?:share|post|upload|email|publish)\b[^.!?]{0,40}\b(?:record|plan|file|group|channel|link)\b",
    re.IGNORECASE,
)


class WorkbenchNavigationPolicy(NavigationPolicy):
    def chat(self, role, message):
        if role == "patient" and isinstance(message, str) and 0 < len(message.strip()) <= 1000 and (
            _CHANGE_PLAN.search(message) or _SHARE.search(message)
        ):
            episode = self._episode
            notice = episode._refer(
                "OUTSIDE_SCOPE", "The request to change or share the plan has been sent for simulated clinician review.", ()
            )
            return {**episode._reply(role, "REFER", notice), "model_calls": 0, "tool_calls": 0,
                    "model_wall_seconds": 0.0, "recovery_attempts": 0, "failure": None, "tool_trace": []}
        return super().chat(role, message)
