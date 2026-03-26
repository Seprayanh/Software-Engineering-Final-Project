import json
import os
from typing import Dict, List, Optional


ROLE_STUDENT = "student"
ROLE_WORKER = "worker"


_DEFAULT_PROFILE: Dict[str, str] = {
    # 空字符串表示“尚未选择身份”
    "role": "",
}


_TAG_PRESETS: Dict[str, List[str]] = {
    ROLE_STUDENT: [
        "学习",
        "作业",
        "考试",
        "复习",
        "论文",
        "实验",
        "课程",
        "小组",
        "报告",
        "签到",
    ],
    ROLE_WORKER: [
        "会议",
        "项目",
        "客户",
        "汇报",
        "跟进",
        "需求",
        "设计",
        "开发",
        "测试",
        "报销",
        "出差",
        "KPI",
    ],
}


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def profile_path() -> str:
    return os.path.join(_project_root(), "profile.json")


def get_tag_presets(role: str) -> List[str]:
    role = (role or "").strip().lower()
    if role not in _TAG_PRESETS:
        role = ROLE_STUDENT
    return list(_TAG_PRESETS.get(role, []))


def get_role_label(role: str) -> str:
    role = (role or "").strip().lower()
    if role == ROLE_STUDENT:
        return "学生"
    if role == ROLE_WORKER:
        return "上班族"
    return "未选择"


def load_profile() -> Dict[str, str]:
    data: Dict[str, str] = dict(_DEFAULT_PROFILE)

    # (A) file profile.json
    try:
        p = profile_path()
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
        if isinstance(j, dict) and (j.get("role") or "").strip():
            data["role"] = str(j.get("role")).strip().lower()
    except Exception:
        pass

    # (B) env override
    env_role = os.environ.get("TODOPRO_ROLE") or os.environ.get("TODO_ROLE")
    if env_role and env_role.strip():
        data["role"] = env_role.strip().lower()

    # 允许 role 为空表示未选择；如果非空且非法则清空
    if data["role"] and data["role"] not in (ROLE_STUDENT, ROLE_WORKER):
        data["role"] = ""
    return data


def save_profile(role: str) -> Dict[str, str]:
    role = (role or "").strip().lower()
    if role not in (ROLE_STUDENT, ROLE_WORKER):
        role = ROLE_STUDENT
    data = {"role": role}
    p = profile_path()
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # ignore write errors (e.g., read-only fs)
        pass
    return data


def choose_role_cli(console=None, require_choice: bool = True) -> Dict[str, str]:
    """CLI 中的身份选择（学生 / 上班族）。

    - 若 profile.json 已有 role，则直接返回。
    - 若没有且 require_choice=True，则弹出选择并保存。
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt

    c = console or Console()
    prof = load_profile()
    cur_role = prof.get("role")
    if cur_role in (ROLE_STUDENT, ROLE_WORKER):
        # 每次进入交互模式都给一次“确认/切换”的机会
        if not require_choice:
            return prof
        c.print(Panel(
            f"当前身份: {get_role_label(cur_role)}\n\n[1] 继续进入系统\n[2] 切换身份",
            title="🪪 身份确认",
            border_style="cyan",
        ))
        ch = Prompt.ask("请选择", choices=["1", "2"], default="1")
        if ch == "1":
            return prof

    # 未设置 or 用户选择切换
    c.print(Panel("请选择你的身份（会影响标签推荐）\n\n[1] 学生\n[2] 上班族", title="🪪 身份选择", border_style="cyan"))
    choice = Prompt.ask("输入 1 或 2", choices=["1", "2"], default="1")
    role = ROLE_STUDENT if choice == "1" else ROLE_WORKER
    return save_profile(role)


def build_profile_payload() -> Dict[str, object]:
    prof = load_profile()
    role = (prof.get("role") or "").strip().lower()
    used_role = role if role in (ROLE_STUDENT, ROLE_WORKER) else ROLE_STUDENT
    return {
        "role": role,
        "role_label": get_role_label(role),
        "tag_presets": get_tag_presets(used_role),
        "roles": [
            {"role": ROLE_STUDENT, "label": "学生", "tag_presets": get_tag_presets(ROLE_STUDENT)},
            {"role": ROLE_WORKER, "label": "上班族", "tag_presets": get_tag_presets(ROLE_WORKER)},
        ],
    }
