import json
import os
from typing import Dict, Optional


_DEFAULT = {
    "name": "肖瑞",
    "student_id": "1230006856",
    "message": "本系统为课程项目演示。进入系统前请确认使用者信息。",
}


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def load_identity() -> Dict[str, str]:
    data: Dict[str, str] = dict(_DEFAULT)

    # (A) project root identity.json
    try:
        p = os.path.join(_project_root(), "identity.json")
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
        if isinstance(j, dict):
            for k in ("name", "student_id", "message"):
                v = j.get(k)
                if v is not None and str(v).strip():
                    data[k] = str(v).strip()
    except Exception:
        pass

    # (B) env overrides
    name = os.environ.get("TODOPRO_NAME")
    sid = os.environ.get("TODOPRO_STUDENT_ID") or os.environ.get("TODOPRO_SID")
    msg = os.environ.get("TODOPRO_IDENTITY_MSG")
    if name and name.strip():
        data["name"] = name.strip()
    if sid and sid.strip():
        data["student_id"] = sid.strip()
    if msg and msg.strip():
        data["message"] = msg.strip()

    return data


def format_identity_text(data: Optional[Dict[str, str]] = None) -> str:
    d = data or load_identity()
    name = (d.get("name") or "").strip()
    sid = (d.get("student_id") or "").strip()
    message = (d.get("message") or "").strip()

    lines = [
        f"姓名: {name}" if name else "姓名: （未设置）",
        f"学号: {sid}" if sid else "学号: （未设置）",
    ]
    if message:
        lines.extend(["", message])
    return "\n".join(lines).strip()


def print_identity_reminder(console=None, require_ack: bool = False, title: str = "身份提醒"):
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align

    c = console or Console()
    d = load_identity()
    body = format_identity_text(d) + "\n\n继续使用表示你已确认以上信息。"
    c.print(Panel(Align.left(body), title=f"🪪 {title}", border_style="cyan"))

    if require_ack:
        try:
            c.input("按 Enter 进入系统...")
        except EOFError:
            pass

    return d
