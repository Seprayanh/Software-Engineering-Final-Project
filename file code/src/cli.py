import click
import os
import sys
import json
from time import sleep
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm

from src.database import TaskManager
from src.reminder import ReminderService
from src.utils import extract_natural_datetime, format_dt
from src.profile import choose_role_cli, load_profile, get_tag_presets, get_role_label


console = Console()
db = TaskManager()
reminder = ReminderService(db)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """TODO Pro 命令行工具（支持交互 + 参数化命令）。"""
    pass


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    clear_screen()
    stats = db.get_stats()
    prof = load_profile()
    role_label = get_role_label(prof.get("role"))
    subtitle = f"交互模式 v2.0  |  未完成 {stats.get('pending', 0)}  |  逾期 {stats.get('overdue', 0)}"
    subtitle = f"{subtitle}  |  身份 {role_label}"
    console.print(
        Panel.fit(
            "[bold white]🎯 TODO Pro 任务管理系统[/bold white]\n"
            "[dim]按数字键选择操作，随时掌控生活[/dim]",
            style="bold blue",
            subtitle=subtitle,
        )
    )


def _priority_label(p: int) -> str:
    return {3: "🔥 高", 2: "⚠️ 中", 1: "☕ 低"}.get(int(p or 2), "⚠️ 中")


def _status_label(s: str) -> str:
    if s == "completed":
        return "[green]✅ 完成[/green]"
    return "[yellow]⏳ 进行中[/yellow]"


def _render_tasks(tasks: List[dict], *, show_notes: bool = False):
    if not tasks:
        console.print(Panel("📭 当前没有任何任务，快去添加一个吧！", style="yellow"))
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("内容", style="white")
    table.add_column("优先级", justify="center")
    table.add_column("分类", style="blue")
    table.add_column("截止", style="white", width=19)
    table.add_column("标签", style="white")
    table.add_column("状态", justify="center")

    for t in tasks:
        content = t.get("content", "")
        if t.get("status") == "completed":
            content = f"[dim strike]{content}[/dim strike]"
        elif t.get("is_overdue"):
            content = f"[bold red]{content}[/bold red]"

        if show_notes and t.get("notes"):
            # 备注只展示一小段，避免占屏
            notes = str(t.get("notes")).strip().replace("\n", " ")
            if len(notes) > 30:
                notes = notes[:30] + "…"
            content = f"{content}\n[dim]{notes}[/dim]"

        deadline = t.get("deadline") or ""
        tags = t.get("tags") or []
        tags_s = ",".join(tags)

        table.add_row(
            str(t.get("id")),
            content,
            _priority_label(t.get("priority")),
            t.get("category") or "通用",
            deadline,
            tags_s,
            _status_label(t.get("status")),
        )

    console.print(table)


# -------------------- 参数化命令 --------------------


@cli.command("add")
@click.argument("content", required=False)
@click.option("--priority", "-p", type=click.IntRange(1, 3), default=2, show_default=True)
@click.option("--category", "-c", default="通用", show_default=True)
@click.option("--deadline", "-d", default=None, help="YYYY-MM-DD HH:MM 或 YYYY-MM-DDTHH:MM")
@click.option("--notes", default=None, help="任务备注/详情（可多行）")
@click.option("--tag", "tags", multiple=True, help="标签（可重复使用 --tag）")
@click.option("--repeat", default=None, help="daily/weekly/monthly 或自定义 RRULE")
@click.option("--rrule", default=None, help="自定义 RRULE（优先于 --repeat）")
@click.option("--nl/--no-nl", default=True, show_default=True, help="从内容自动解析日期时间")
def add_cmd(content: Optional[str], priority: int, category: str, deadline: Optional[str], notes: Optional[str], tags: tuple, repeat: Optional[str], rrule: Optional[str], nl: bool):
    """添加任务（支持 stdin 导入）。

    用法：
      python main.py add "明天下午3点交报告" --tag 学习 --repeat weekly
      echo -e "任务1\n任务2" | python main.py add - --category 工作
    """
    # stdin import
    if content == "-":
        raw = sys.stdin.read()
        lines = [x.strip() for x in raw.splitlines() if x.strip()]
        if not lines:
            raise click.ClickException("stdin 为空")
        created = 0
        for line in lines:
            dl = deadline
            if not dl and nl:
                dt = extract_natural_datetime(line)
                if dt:
                    dl = format_dt(dt)
            db.add_task(
                content=line,
                priority=priority,
                category=category,
                deadline=dl,
                notes=notes,
                tags=list(tags),
                rrule=(rrule or repeat),
            )
            created += 1
        console.print(f"✅ 已导入 {created} 条任务", style="green")
        return

    if not content:
        raise click.ClickException("缺少任务内容。可用: python main.py add \"...\" 或从 stdin: python main.py add -")

    if not deadline and nl:
        dt = extract_natural_datetime(content)
        if dt:
            deadline = format_dt(dt)

    task_id = db.add_task(
        content=content,
        priority=priority,
        category=category,
        deadline=deadline,
        notes=notes,
        tags=list(tags),
        rrule=(rrule or repeat),
    )
    console.print(f"✅ 添加成功！ID={task_id}", style="green")


@cli.command("list")
@click.option("--status", type=click.Choice(["pending", "completed"], case_sensitive=False), default=None)
@click.option("--category", default=None)
@click.option("--tag", default=None)
@click.option("--overdue", is_flag=True, help="只看逾期")
@click.option("--q", default=None, help="关键词搜索（content/notes）")
@click.option("--sort", type=click.Choice(["id", "created_at", "updated_at", "deadline", "priority", "status", "category"], case_sensitive=False), default=None)
@click.option("--order", type=click.Choice(["asc", "desc"], case_sensitive=False), default="desc")
@click.option("--page", default=1, show_default=True)
@click.option("--page-size", default=50, show_default=True)
@click.option("--json", "as_json", is_flag=True, help="输出 JSON")
@click.option("--show-notes", is_flag=True, help="列表中显示备注摘要")
def list_cmd(status, category, tag, overdue, q, sort, order, page, page_size, as_json, show_notes):
    """列出任务（分页/过滤/排序）。"""
    filters = {
        "status": status,
        "category": category,
        "tag": tag,
        "q": q,
        "overdue": True if overdue else None,
    }
    result = db.get_tasks(filters=filters, page=page, page_size=page_size, sort=sort, order=order)

    if as_json:
        console.print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    items = result.get("items", [])
    _render_tasks(items, show_notes=show_notes)
    console.print(
        f"\n[dim]Total={result.get('total')} | page={result.get('page')} | page_size={result.get('page_size')}[/dim]"
    )


@cli.command("done")
@click.argument("ids", nargs=-1, type=int, required=True)
def done_cmd(ids):
    """完成任务（支持多个 ID）。完成重复任务会自动生成下一次。"""
    ok = 0
    for i in ids:
        if db.set_status(int(i), "completed"):
            ok += 1
    console.print(f"✅ 已完成 {ok}/{len(ids)}", style="green")


@cli.command("del")
@click.argument("ids", nargs=-1, type=int, required=True)
@click.option("-y", "--yes", is_flag=True, help="不询问直接删除")
def del_cmd(ids, yes):
    """删除任务（支持多个 ID）。"""
    if not yes:
        if not Confirm.ask(f"确定要删除 {len(ids)} 条任务吗？"):
            return
    deleted = 0
    for i in ids:
        if db.delete_task(int(i)):
            deleted += 1
    console.print(f"🗑️ 已删除 {deleted}/{len(ids)}", style="yellow")


@cli.command("postpone")
@click.argument("task_id", type=int)
@click.option("--days", type=int, default=1, show_default=True)
@click.option("--week", is_flag=True, help="等价于 --days 7")
def postpone_cmd(task_id: int, days: int, week: bool):
    """延期：+N 天（常用 +1 天 / +1 周）。"""
    if week:
        days = 7
    if db.postpone_task(task_id, days):
        console.print(f"⏭️ 已延期 {days} 天 (ID={task_id})", style="green")
    else:
        console.print("❌ ID 不存在", style="red")


@cli.command("batch")
@click.option("--action", type=click.Choice(["complete", "delete", "category", "status", "postpone"], case_sensitive=False), required=True)
@click.option("--ids", required=True, help="逗号分隔，例如 1,2,3")
@click.option("--category", default=None)
@click.option("--status", default=None)
@click.option("--days", type=int, default=None)
def batch_cmd(action, ids, category, status, days):
    """批量操作（完成/删除/改分类/改状态/延期）。"""
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    payload = {"category": category, "status": status, "days": days}
    res = db.batch_action(id_list, action, payload)
    if res.get("success"):
        console.print(f"✅ 批量操作完成：updated={res.get('updated')} deleted={res.get('deleted')}")
        if res.get("errors"):
            console.print("[dim]" + "\n".join(res.get("errors")) + "[/dim]")
    else:
        console.print(f"❌ 批量操作失败：{res}", style="red")


@cli.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish", "powershell"], case_sensitive=False), required=True)
def completion_cmd(shell: str):
    """输出 shell 自动补全脚本。用法：

    python main.py completion bash > todopro-complete.bash
    source todopro-complete.bash
    """
    try:
        from click.shell_completion import get_completion_script

        # 尽量取稳定 prog_name
        prog = os.environ.get("TODOPRO_PROG") or os.path.basename(sys.argv[0])
        prog = prog.strip() or "todopro"
        complete_var = "_" + prog.upper().replace("-", "_").replace(".", "_") + "_COMPLETE"
        script = get_completion_script(prog_name=prog, complete_var=complete_var, shell=shell)
        click.echo(script)
    except Exception as e:
        raise click.ClickException(f"生成补全脚本失败: {e}")


@cli.command("stats")
def stats_cmd():
    """显示统计信息。"""
    s = db.get_stats()
    console.print(
        Panel(
            f"未完成: {s.get('pending')}\n已完成: {s.get('completed')}\n逾期: {s.get('overdue')}\n时间: {s.get('now')}",
            title="📊 统计",
            style="blue",
        )
    )



@cli.command("web")
@click.option("--port", "-p", type=int, default=8000, show_default=True)
def web_cmd(port: int):
    """启动 Web 界面与 REST API。"""
    from src.web import run_server

    run_server(port=port)

@cli.command("web")
@click.option("--port", "-p", type=int, default=8000, show_default=True)
def web_cmd(port: int):
    """启动 Web 界面与 REST API。"""
    from src.web import run_server
    run_server(port=port)

@cli.command("web")
@click.option("--port", "-p", type=int, default=8000, show_default=True)
def web_cmd(port: int):
    """启动 Web 界面与 REST API。"""
    from src.web import run_server

    run_server(port=port)
# -------------------- 交互模式 --------------------


def show_tasks_logic(pause: bool = True):
    tasks = db.get_tasks(page=1, page_size=200).get("items", [])
    _render_tasks(tasks, show_notes=True)
    if pause:
        Prompt.ask("\n按回车键返回菜单")


def add_task_logic():
    console.print("[bold green]📝 添加新任务[/bold green]")
    content = Prompt.ask("任务内容")
    if not content:
        return

    console.print("优先级: [1]低 [2]中 [3]高")
    p_choice = IntPrompt.ask("请选择", choices=["1", "2", "3"], default=2)

    console.print("分类: [1]工作 [2]学习 [3]生活 [4]其他 [5]通用")
    cat_map = {"1": "工作", "2": "学习", "3": "生活", "4": "其他", "5": "通用"}
    c_choice = Prompt.ask("请选择", choices=["1", "2", "3", "4", "5"], default="5")

    deadline = Prompt.ask("截止时间(可空，支持自然语言)", default="")
    deadline = deadline.strip() or None
    if not deadline:
        dt = extract_natural_datetime(content)
        if dt:
            deadline = format_dt(dt)

    notes = Prompt.ask("备注/详情(可空)", default="")
    notes = notes.strip() or None

    # 根据身份显示标签推荐
    prof = load_profile()
    presets = get_tag_presets(prof.get("role"))
    if presets:
        console.print("\n[dim]快捷标签（可直接输入编号，多个用逗号）：[/dim]")
        console.print("  " + "  ".join([f"[{i+1}]{t}" for i, t in enumerate(presets)]))
        pick = Prompt.ask("选择标签编号(可空)", default="").strip()
        chosen = []
        if pick:
            for part in pick.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(presets):
                        chosen.append(presets[idx])
        custom = Prompt.ask("自定义标签(逗号分隔，可空)", default="").strip()
        all_tags = chosen
        if custom:
            all_tags.extend([x.strip() for x in custom.split(",") if x.strip()])
        # 去重保持顺序
        seen = set()
        all_tags = [x for x in all_tags if not (x in seen or seen.add(x))]
        tags = ",".join(all_tags)
    else:
        tags = Prompt.ask("标签(逗号分隔，可空)", default="").strip()

    repeat = Prompt.ask("重复任务: none/daily/weekly/monthly/自定义RRULE(可空)", default="")
    repeat = repeat.strip() or None

    db.add_task(content, p_choice, cat_map[c_choice], deadline=deadline, notes=notes, tags=tags, rrule=repeat)
    console.print("✅ 添加成功！", style="green")
    sleep(0.6)


def complete_task_logic():
    show_tasks_logic(pause=False)
    console.print("\n[bold cyan]✅ 标记完成[/bold cyan]")
    task_id = IntPrompt.ask("请输入要完成的任务ID (输入 0 返回)")
    if task_id == 0:
        return

    if db.set_status(task_id, "completed"):
        console.print("🎉 恭喜！任务已完成！（若为重复任务，会自动生成下一次）", style="green")
        sleep(0.8)
    else:
        console.print("❌ ID 不存在", style="red")
        sleep(1)


def delete_task_logic():
    show_tasks_logic(pause=False)
    console.print("\n[bold red]🗑️ 删除任务[/bold red]")
    task_id = IntPrompt.ask("请输入要删除的任务ID (输入 0 返回)")
    if task_id == 0:
        return

    if Confirm.ask(f"确定要删除 ID {task_id} 吗？"):
        if db.delete_task(task_id):
            console.print("✅ 已删除", style="yellow")
            sleep(0.8)
        else:
            console.print("❌ ID 不存在", style="red")
            sleep(1)


def postpone_task_logic():
    show_tasks_logic(pause=False)
    console.print("\n[bold yellow]⏭️ 延期[/bold yellow]")
    task_id = IntPrompt.ask("请输入要延期的任务ID (输入 0 返回)")
    if task_id == 0:
        return
    console.print("[1] +1 天  [2] +1 周")
    ch = Prompt.ask("请选择", choices=["1", "2"], default="1")
    days = 1 if ch == "1" else 7
    if db.postpone_task(task_id, days):
        console.print(f"✅ 已延期 {days} 天", style="green")
        sleep(0.6)
    else:
        console.print("❌ ID 不存在", style="red")
        sleep(1)

# -------------------- alarm (闹钟提醒) --------------------

@cli.group("alarm")
def alarm_group():
    """闹钟提醒功能（创建/查看/删除/后台触发）。"""
    pass


@alarm_group.command("add")
@click.argument("message", required=False, default="")
@click.option("--at", "fire_at", default=None, help='提醒时间，例如 "2025-12-20 15:00" 或 "2025-12-20T15:00"')
@click.option("--task", "task_id", default=None, type=int, help="绑定到某个任务 ID（会从任务 deadline 计算提醒时间）")
@click.option("--before", "before_minutes", default=0, type=int, help="提前多少分钟提醒（配合 --task 使用）")
def alarm_add(message: str, fire_at: Optional[str], task_id: Optional[int], before_minutes: int):
    """添加闹钟提醒。

    示例：
      python main.py alarm add "喝水" --at "2025-12-20 15:00"
      python main.py alarm add --task 3 --before 30
    """
    payload = {
        "title": message or "",
        "fire_at": fire_at,
        "task_id": task_id,
        "before_minutes": before_minutes,
    }
    try:
        alarm_id = db.create_alarm_from_payload(payload)
    except Exception as e:
        raise click.ClickException(str(e))
    console.print(f"[green]✅ 已创建提醒[/green]  ID={alarm_id}")


@alarm_group.command("list")
@click.option("--pending", is_flag=True, help="只看未触发的提醒")
def alarm_list(pending: bool):
    """查看闹钟提醒列表。"""
    items = db.list_alarms(pending_only=pending)
    if not items:
        console.print(Panel("📭 暂无提醒", style="yellow"))
        return
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("时间", style="white", width=19)
    table.add_column("内容", style="white")
    table.add_column("状态", justify="center", width=8)
    table.add_column("任务ID", justify="center", width=8)
    for a in items:
        st = "[green]待触发[/green]" if int(a.get("is_done") or 0) == 0 else "[dim]已触发[/dim]"
        table.add_row(
            str(a.get("id")),
            str(a.get("fire_at") or ""),
            str(a.get("title") or ""),
            st,
            str(a.get("task_id") or ""),
        )
    console.print(table)


@alarm_group.command("done")
@click.argument("alarm_id", type=int)
def alarm_done(alarm_id: int):
    """手动标记提醒为已完成（不会再触发）。"""
    ok = db.mark_alarm_done(alarm_id)
    if ok:
        console.print("[green]✅ 已标记完成[/green]")
    else:
        console.print("[red]❌ 未找到该提醒 ID[/red]")


@alarm_group.command("del")
@click.argument("alarm_id", type=int)
def alarm_del(alarm_id: int):
    """删除提醒。"""
    ok = db.delete_alarm(alarm_id)
    if ok:
        console.print("[green]🗑️ 已删除[/green]")
    else:
        console.print("[red]❌ 未找到该提醒 ID[/red]")


@alarm_group.command("run")
@click.option("--poll", default=10, type=int, help="轮询秒数（默认 10）")
def alarm_run(poll: int):
    """后台运行提醒服务（不启动 Web）。

    用 Ctrl+C 退出。
    """
    reminder.poll_seconds = int(poll)
    reminder.start()
    console.print("[bold green]⏰ 提醒服务已启动[/bold green]（Ctrl+C 退出）")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        console.print("\n[dim]已退出提醒服务[/dim]")


@cli.command()
def interactive():
    """启动交互式菜单模式"""
    # 进入系统前选择身份（学生 / 上班族），用于标签推荐
    try:
        choose_role_cli(console=console, require_choice=True)
    except Exception:
        pass
    # 启动闹钟提醒后台线程（交互模式下也能弹通知）
    reminder.start()
    while True:
        print_header()
        console.print("[bold]功能菜单：[/bold]")
        console.print(" [1] 📋 查看所有任务")
        console.print(" [2] ➕ 添加新任务")
        console.print(" [3] ✅ 完成任务")
        console.print(" [4] 🗑️ 删除任务")
        console.print(" [5] ⏭️ 延期 (+1天/+1周)")
        console.print(" [0] 🚪 退出系统")

        choice = Prompt.ask("\n请选择", choices=["1", "2", "3", "4", "5", "0"])

        if choice == "1":
            print_header()
            show_tasks_logic()
        elif choice == "2":
            print_header()
            add_task_logic()
        elif choice == "3":
            print_header()
            complete_task_logic()
        elif choice == "4":
            print_header()
            delete_task_logic()
        elif choice == "5":
            print_header()
            postpone_task_logic()
        elif choice == "0":
            console.print("👋 再见！")
            break


@cli.command()
def init():
    """（保留兼容）初始化数据库。"""
    # 初始化动作在 TaskManager 构造时已经完成
    console.print("✅ 数据库已就绪", style="green")
