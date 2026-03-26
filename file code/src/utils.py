import re
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def now_local() -> datetime:
    # 项目内部使用“无时区 datetime”，默认以本机时区为准
    return datetime.now()


def format_dt(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.strftime(_DT_FMT)


def parse_dt(s: Optional[str], date_only_eod: bool = True) -> Optional[datetime]:
    """Parse several common datetime formats.

    - Supports HTML <input type=datetime-local> : YYYY-MM-DDTHH:MM
    - Supports date-only: YYYY-MM-DD (defaults to end-of-day if date_only_eod=True)
    """
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None

    # common normalize
    s = s.replace("/", "-")

    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            if fmt == "%Y-%m-%d":
                if date_only_eod:
                    dt = dt.replace(hour=23, minute=59, second=59)
                else:
                    dt = dt.replace(hour=0, minute=0, second=0)
            return dt
        except ValueError:
            continue
    return None


def normalize_deadline(s: Optional[str]) -> Optional[str]:
    dt = parse_dt(s)
    return format_dt(dt)


# -------- tag helpers --------

def normalize_tags(tags: Any) -> List[str]:
    """Accept list[str] / comma string / space separated string and normalize to unique list."""
    if tags is None:
        return []

    raw: List[str] = []
    if isinstance(tags, list):
        raw = [str(x) for x in tags]
    elif isinstance(tags, str):
        # 支持逗号/中文逗号/空格/分号
        parts = re.split(r"[，,;；\n\t ]+", tags.strip())
        raw = [p for p in parts if p]
    else:
        raw = [str(tags)]

    seen = set()
    out: List[str] = []
    for t in raw:
        t = t.strip()
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def dump_tags(tags: Any) -> str:
    return json.dumps(normalize_tags(tags), ensure_ascii=False)


def load_tags(tags_json: Optional[str]) -> List[str]:
    if not tags_json:
        return []
    try:
        v = json.loads(tags_json)
        if isinstance(v, list):
            return normalize_tags(v)
        if isinstance(v, str):
            return normalize_tags(v)
        return []
    except Exception:
        # 兼容旧数据：逗号字符串
        return normalize_tags(tags_json)


# -------- RRULE (minimal) --------

_WEEKDAY_MAP = {
    "MO": 0,
    "TU": 1,
    "WE": 2,
    "TH": 3,
    "FR": 4,
    "SA": 5,
    "SU": 6,
}


def preset_to_rrule(preset: Optional[str]) -> Optional[str]:
    if not preset:
        return None
    p = preset.strip().lower()
    if p in ("none", "no", "0"):
        return None
    if p in ("daily", "everyday", "day"):
        return "FREQ=DAILY;INTERVAL=1"
    if p in ("weekly", "week"):
        return "FREQ=WEEKLY;INTERVAL=1"
    if p in ("monthly", "month"):
        return "FREQ=MONTHLY;INTERVAL=1"
    # allow passing full rrule
    if p.startswith("rrule:"):
        return preset.strip()[6:]
    return preset  # treat as raw RRULE string


def normalize_rrule(rrule: Optional[str]) -> Optional[str]:
    """Alias: accept daily/weekly/monthly or raw RRULE."""
    return preset_to_rrule(rrule)


def parse_rrule(rrule: Optional[str]) -> Optional[Dict[str, str]]:
    if not rrule:
        return None
    r = rrule.strip()
    if not r:
        return None
    if r.upper().startswith("RRULE:"):
        r = r.split(":", 1)[1]
    parts = [p for p in r.split(";") if p]
    out: Dict[str, str] = {}
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        out[k.strip().upper()] = v.strip()
    if "FREQ" not in out:
        return None
    out["FREQ"] = out["FREQ"].upper()
    return out


def _add_months(dt: datetime, months: int) -> datetime:
    # 手写 add_months：保持 day 尽量不越界
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    # 处理月底
    day = dt.day
    # 找目标月最大天数
    if m == 12:
        next_month = datetime(y + 1, 1, 1)
    else:
        next_month = datetime(y, m + 1, 1)
    last_day = (next_month - timedelta(days=1)).day
    day = min(day, last_day)
    return dt.replace(year=y, month=m, day=day)


def _parse_until(v: str) -> Optional[datetime]:
    v = v.strip()
    # support 20251231T235959Z / 20251231T235959 / 2025-12-31 23:59
    m = re.fullmatch(r"(\d{8})(T(\d{6}))?Z?", v)
    if m:
        ymd = m.group(1)
        hms = m.group(3)
        y = int(ymd[0:4]); mo = int(ymd[4:6]); d = int(ymd[6:8])
        if hms:
            hh = int(hms[0:2]); mm = int(hms[2:4]); ss = int(hms[4:6])
            return datetime(y, mo, d, hh, mm, ss)
        return datetime(y, mo, d, 23, 59, 59)
    # fallback
    return parse_dt(v)


def next_occurrence(base: datetime, rrule_str: str, occurrence_idx: int) -> Optional[datetime]:
    """Compute next occurrence after 'base' using a minimal subset of RRULE.

    Supported: FREQ=DAILY|WEEKLY|MONTHLY, INTERVAL, BYDAY (weekly), BYMONTHDAY (monthly), COUNT, UNTIL.
    """
    rule = parse_rrule(rrule_str)
    if not rule:
        return None

    # COUNT
    if "COUNT" in rule:
        try:
            count = int(rule["COUNT"])
            # occurrence_idx starts at 0 for the first task in series
            if occurrence_idx + 1 >= count:
                return None
        except Exception:
            pass

    interval = 1
    if "INTERVAL" in rule:
        try:
            interval = max(1, int(rule["INTERVAL"]))
        except Exception:
            interval = 1

    freq = rule.get("FREQ", "").upper()

    candidate: Optional[datetime] = None

    if freq == "DAILY":
        candidate = base + timedelta(days=interval)

    elif freq == "WEEKLY":
        byday = rule.get("BYDAY")
        days: List[int] = []
        if byday:
            for token in byday.split(","):
                token = token.strip().upper()
                if token in _WEEKDAY_MAP:
                    days.append(_WEEKDAY_MAP[token])
            days.sort()

        if not days:
            # default: same weekday
            candidate = base + timedelta(weeks=interval)
        else:
            # find next weekday in the same week; if none, jump interval weeks and pick first
            cur_wd = base.weekday()
            for d in days:
                if d > cur_wd:
                    candidate = base + timedelta(days=(d - cur_wd))
                    break
            if candidate is None:
                # next interval week (start from base + interval weeks) then go to first BYDAY
                jump = base + timedelta(weeks=interval)
                jump_wd = jump.weekday()
                first = days[0]
                candidate = jump + timedelta(days=(first - jump_wd) % 7)

    elif freq == "MONTHLY":
        bymonthday = rule.get("BYMONTHDAY")
        if bymonthday:
            try:
                target_day = int(bymonthday.split(",")[0].strip())
            except Exception:
                target_day = base.day
        else:
            target_day = base.day

        cand = _add_months(base, interval)
        # adjust to target_day within month
        # compute last day
        if cand.month == 12:
            next_month = datetime(cand.year + 1, 1, 1)
        else:
            next_month = datetime(cand.year, cand.month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        cand_day = min(max(1, target_day), last_day)
        candidate = cand.replace(day=cand_day)

    else:
        # unsupported
        return None

    # UNTIL
    if candidate is not None and "UNTIL" in rule:
        until = _parse_until(rule["UNTIL"])
        if until is not None and candidate > until:
            return None

    return candidate


# -------- Natural language datetime (minimal, CN + EN) --------

_CN_WEEK = {
    "一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6,
}


def _extract_time(text: str) -> Optional[Tuple[int, int]]:
    # HH:MM
    m = re.search(r"(?<!\d)(\d{1,2})[:：](\d{2})(?!\d)", text)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2))
        return (hh, mm)

    # 3pm / 3:30pm
    m = re.search(r"(?<!\d)(\d{1,2})(?:[:：](\d{2}))?\s*(am|pm)(?!\w)", text, re.I)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2) or 0)
        ap = m.group(3).lower()
        if ap == "pm" and hh < 12:
            hh += 12
        if ap == "am" and hh == 12:
            hh = 0
        return (hh, mm)

    # 3点 / 3点半 / 3点15分
    m = re.search(r"(?<!\d)(\d{1,2})\s*点(?:\s*(半)|\s*(\d{1,2})\s*分)?", text)
    if m:
        hh = int(m.group(1))
        if m.group(2):
            mm = 30
        elif m.group(3):
            mm = int(m.group(3))
        else:
            mm = 0
        return (hh, mm)

    return None


def _apply_daypart(text: str, hh: int) -> int:
    # 上午/下午/晚上/中午
    if re.search(r"下午|晚上|傍晚", text) and hh < 12:
        return hh + 12
    if re.search(r"中午", text) and hh < 11:
        return hh + 12
    if re.search(r"凌晨", text):
        return hh  # keep
    return hh


def extract_natural_datetime(text: str, base: Optional[datetime] = None) -> Optional[datetime]:
    """Try to extract a datetime from natural language in text.

    Very small, heuristic parser (no third-party deps).
    """
    if not text:
        return None

    base = base or now_local()
    t = text.strip()

    # 1) explicit date: YYYY-MM-DD / YYYY/MM/DD
    m = re.search(r"(\d{4})[\-/](\d{1,2})[\-/](\d{1,2})(?:\s*[T ]\s*(\d{1,2})(?::(\d{2}))?)?", t)
    if m:
        y = int(m.group(1)); mo = int(m.group(2)); d = int(m.group(3))
        if m.group(4) is not None:
            hh = int(m.group(4)); mm = int(m.group(5) or 0)
            hh = _apply_daypart(t, hh)
            return datetime(y, mo, d, hh, mm, 0)
        # date only -> end of day
        return datetime(y, mo, d, 23, 59, 59)

    # 2) explicit date: MM-DD / MM/DD
    m = re.search(r"(?<!\d)(\d{1,2})[\-/](\d{1,2})(?:\s*[T ]\s*(\d{1,2})(?::(\d{2}))?)?", t)
    if m:
        y = base.year
        mo = int(m.group(1)); d = int(m.group(2))
        if m.group(3) is not None:
            hh = int(m.group(3)); mm = int(m.group(4) or 0)
            hh = _apply_daypart(t, hh)
            return datetime(y, mo, d, hh, mm, 0)
        return datetime(y, mo, d, 23, 59, 59)

    # 3) relative day words
    day_offset = None
    if "今天" in t or "today" in t.lower():
        day_offset = 0
    elif "明天" in t or "tomorrow" in t.lower():
        day_offset = 1
    elif "后天" in t:
        day_offset = 2
    elif "大后天" in t:
        day_offset = 3

    # 4) weekday words
    weekday_target = None
    is_next_week = False
    m = re.search(r"下周([一二三四五六日天])", t)
    if m:
        weekday_target = _CN_WEEK[m.group(1)]
        is_next_week = True
    else:
        m = re.search(r"(?:周|星期)([一二三四五六日天])", t)
        if m:
            weekday_target = _CN_WEEK[m.group(1)]

    # EN weekday
    if weekday_target is None:
        m = re.search(r"\b(mon|tue|wed|thu|fri|sat|sun)(day)?\b", t, re.I)
        if m:
            token = m.group(1).lower()
            weekday_target = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}[token]
            if re.search(r"\bnext\b", t, re.I):
                is_next_week = True

    # time
    tm = _extract_time(t)

    # pick date
    date_dt: Optional[datetime] = None
    if weekday_target is not None:
        cur = base.weekday()
        delta = (weekday_target - cur) % 7
        if delta == 0:
            delta = 7
        if is_next_week:
            delta += 7 if delta <= 7 else 0
        date_dt = base + timedelta(days=delta)
    elif day_offset is not None:
        date_dt = base + timedelta(days=day_offset)

    if date_dt is not None:
        if tm is None:
            return date_dt.replace(hour=23, minute=59, second=59, microsecond=0)
        hh, mm = tm
        hh = _apply_daypart(t, hh)
        return date_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)

    # if only time mentioned
    if tm is not None:
        hh, mm = tm
        hh = _apply_daypart(t, hh)
        cand = base.replace(hour=hh, minute=mm, second=0, microsecond=0)
        # 如果时间已经过去，默认顺延到明天
        if cand < base:
            cand = cand + timedelta(days=1)
        return cand

    return None
