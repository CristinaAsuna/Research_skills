#!/usr/bin/env python3
"""lab: a shared, git-backed record of what ran where across the user's machines.

Works inside any git project (the project repo is its own shared record). Outside a repo it
falls back to the "hub" repo named in ~/.config/lab/hub. Standard library only; the git calls
avoid `git -C` and `--date=format` so the cluster's git 1.8 works.

    lab status | sync | runs | journal | log "<text>"
    lab run start <exp-id> [--job J] -- <command>      (the command is recorded, not executed)
    lab run end <run-id> --status done|failed|cancelled [--outputs <where>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import socket
import subprocess
import sys
import tarfile
from pathlib import Path

MACHINE_FILE = Path("~/.config/lab/machine")
HUB_FILE = Path("~/.config/lab/hub")
RECORD_DIR = Path(".lab") / "runs"
RUN_STATUSES = ("running", "done", "failed", "cancelled")
EXP_ID = re.compile(r"^[\w][\w.-]*$")
COMMIT_SUBJECT = re.compile(r"^(?P<kind>[a-z0-9]+)(?:\[(?P<machine>[\w-]+)\])?(?:\((?P<exp>[^)]*)\))?:\s*(?P<text>.*)$")


# ---------- git and identity ----------

def git(top: Path, *args: str) -> subprocess.CompletedProcess:
    # cwd instead of `git -C`, so old git (1.8 on the cluster) works too
    return subprocess.run(["git", *args], cwd=str(top), capture_output=True, text=True)


def git_toplevel(path: Path) -> Path | None:
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(path), capture_output=True, text=True)
    except (FileNotFoundError, NotADirectoryError):
        return None
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def first_line(result: subprocess.CompletedProcess) -> str:
    text = (result.stderr or result.stdout).strip()
    return text.splitlines()[0] if text else f"exit {result.returncode}"


def current_machine() -> str:
    """Machine name from $LAB_MACHINE or ~/.config/lab/machine (mac / pc / cluster)."""
    name = os.environ.get("LAB_MACHINE", "").strip()
    path = MACHINE_FILE.expanduser()
    if not name and path.is_file():
        name = path.read_text(encoding="utf-8").strip()
    return name or "unknown"


def hub_path() -> Path | None:
    name = os.environ.get("LAB_HUB", "").strip()
    path = HUB_FILE.expanduser()
    if not name and path.is_file():
        name = path.read_text(encoding="utf-8").strip()
    return Path(name).expanduser() if name else None


def find_root(args: argparse.Namespace) -> Path:
    """--root, else --hub, else the git repo containing the cwd, else the hub."""
    if args.root:
        top = git_toplevel(Path(args.root).expanduser())
        if top is None:
            sys.exit(f"{args.root} 不在 git 仓库里。")
        return top
    hub = hub_path()
    if args.hub:
        if hub is None:
            sys.exit("没有配置总台仓库：写入 ~/.config/lab/hub 或设置 LAB_HUB。")
        top = git_toplevel(hub)
        if top is None:
            sys.exit(f"总台 {hub} 不是 git 仓库。")
        return top
    top = git_toplevel(Path.cwd())
    if top is not None:
        return top
    if hub is not None and git_toplevel(hub) is not None:
        print(f"（当前目录不在 git 仓库里，使用总台 {hub}）")
        return git_toplevel(hub)
    sys.exit("当前目录不在 git 仓库里，也没有配置总台（~/.config/lab/hub）。")


# ---------- commit, push, pull ----------

def commit_and_push(top: Path, message: str, paths: list[Path], push: bool) -> None:
    if paths:
        result = git(top, "add", "--", *[str(p) for p in paths])
        if result.returncode != 0:
            sys.exit(first_line(result))
        # `commit -- <paths>` records only these files and leaves other staged changes alone
        result = git(top, "commit", "-q", "-m", message, "--", *[str(p) for p in paths])
    else:
        if git(top, "diff", "--cached", "--quiet").returncode != 0:
            sys.exit("有已暂存但未提交的改动：先提交或取消暂存，再记录。")
        result = git(top, "commit", "-q", "--allow-empty", "-m", message)
    if result.returncode != 0:
        sys.exit(f"提交失败：{first_line(result)}")
    print(f"已提交：{message}")
    if push:
        push_head(top)


def rebase_onto_remote(top: Path, remote: str) -> bool:
    """Replay local commits onto the remote branch; leave the repo untouched if that fails."""
    if git(top, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        print("WARN 有未提交的改动，无法自动同步：先提交，再运行 lab sync。")
        return False
    branch = git(top, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    result = git(top, "pull", "--rebase", "-q", remote, branch)
    if result.returncode != 0:
        git(top, "rebase", "--abort")
        print(f"WARN 自动 rebase 失败，已恢复原状（{first_line(result)}）：请手动 git pull --rebase 解决冲突后 git push。")
        return False
    return True


def push_head(top: Path) -> bool:
    """Push HEAD; if the remote moved ahead (another machine pushed), rebase once and retry."""
    remotes = git(top, "remote").stdout.split()
    if not remotes:
        return False
    result = git(top, "push", "-q", remotes[0], "HEAD")
    if result.returncode == 0:
        print("已推送。")
        return True
    if not rebase_onto_remote(top, remotes[0]):
        return False
    result = git(top, "push", "-q", remotes[0], "HEAD")
    print("已拉取其他机器的更新并推送。" if result.returncode == 0 else f"WARN 推送失败：{first_line(result)}")
    return result.returncode == 0


def refresh(top: Path, enabled: bool) -> None:
    """Fast-forward to the latest shared state before showing it; never blocks on failure."""
    if not enabled or not git(top, "remote").stdout.strip():
        return
    try:
        result = subprocess.run(["git", "pull", "-q", "--ff-only"], cwd=str(top), capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        print("WARN git pull 超时，以下是本地状态。")
        return
    if result.returncode != 0:
        print(f"WARN git pull 失败，以下是本地状态（{first_line(result)}）；有本机提交时先运行 lab sync。")


# ---------- run records ----------

def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_records(top: Path) -> list[tuple[Path, dict]]:
    records = []
    for path in sorted((top / RECORD_DIR).glob("*.json")):
        try:
            records.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, UnicodeDecodeError):
            records.append((path, {"run_id": path.stem, "status": "invalid"}))
    return records


def dirty_code(top: Path) -> list[str]:
    """Uncommitted or untracked non-Markdown files: they would be missing from the snapshot."""
    lines = git(top, "status", "--porcelain").stdout.splitlines()
    paths = [line[3:].split(" -> ")[-1].strip('"') for line in lines if len(line) > 3]
    return [p for p in paths if not p.endswith(".md")]


def project_dir(top: Path) -> Path:
    """The research project the cwd is in: the nearest directory up to the repo root holding
    STATE.md and EXPERIMENTS.md (a sub-project in a shared repo), else the repo root."""
    here = Path.cwd().resolve()
    if here != top and top not in here.parents:
        return top
    for path in (here, *here.parents):
        if (path / "STATE.md").is_file() and (path / "EXPERIMENTS.md").is_file():
            return path
        if path == top:
            break
    return top


def cmd_run_start(args: argparse.Namespace) -> int:
    top = find_root(args)
    command = " ".join(args.cmd).strip()
    if not command:
        sys.exit("请在 -- 之后给出要运行的命令。")
    if not EXP_ID.match(args.exp):
        sys.exit("实验编号只能包含字母、数字、下划线、点和连字符。")
    me = current_machine()
    if me == "unknown":
        sys.exit("不知道本机是哪台：请写 ~/.config/lab/machine（mac / pc / cluster）或设置 LAB_MACHINE。")
    dirty = dirty_code(top)
    if dirty:
        sys.exit(f"有 {len(dirty)} 个文件未提交（例如 {dirty[0]}）：先提交代码，运行记录才能指向确定的版本。")
    commit = git(top, "rev-parse", "HEAD").stdout.strip()
    if not commit:
        sys.exit("仓库还没有任何提交。")
    project = project_dir(top)
    prefix = project.relative_to(top).as_posix()
    runs_root = Path(os.environ.get("LAB_RUNS_ROOT") or (project / "runs")).expanduser()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{args.exp}-{stamp}-{me}"
    run_dir = runs_root / args.exp / run_id
    try:
        probe = (run_dir / ".probe").resolve().relative_to(top).as_posix()
    except ValueError:
        probe = None
    if probe and git(top, "check-ignore", "-q", probe).returncode != 0:
        print(f"WARN {run_dir} 在仓库内但没有被 git 忽略：把 /runs/ 写进 .gitignore，或设置 LAB_RUNS_ROOT。")
    run_dir.mkdir(parents=True, exist_ok=False)
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"] + ([] if prefix == "." else [prefix]),
                             cwd=str(top), capture_output=True)
    if archive.returncode != 0:
        sys.exit(archive.stderr.decode(errors="replace").strip())
    code_dir = run_dir / "code"
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        try:
            tar.extractall(str(code_dir), filter="data")
        except TypeError:  # Python without extraction filters
            tar.extractall(str(code_dir))
    record = {"run_id": run_id, "exp": args.exp, "repo": top.name, "project": prefix, "machine": me, "host": socket.gethostname(),
              "run_dir": str(run_dir.resolve()), "code_dir": str(code_dir.resolve()), "command": command,
              "commit": commit, "started": dt.datetime.now().isoformat(timespec="seconds"), "ended": None,
              "status": "running", "job": args.job, "note": args.note}
    path = top / RECORD_DIR / f"{run_id}.json"
    write_json(path, record)
    print(f"运行 {run_id}：机器 {me}，目录 {run_dir}")
    print(f"代码快照（提交 {commit[:8]}）：{code_dir}")
    commit_and_push(top, f"run[{me}]({args.exp}): start {run_id}", [path], push=not args.no_push)
    if not args.job:
        work = code_dir if prefix == "." else code_dir / prefix
        print(f"建议在 tmux 中启动：tmux new -d -s {run_id} 'cd {work} && {command} 2>&1 | tee {run_dir}/run.log'")
    return 0


def cmd_run_end(args: argparse.Namespace) -> int:
    top = find_root(args)
    matches = [(p, r) for p, r in run_records(top) if r.get("run_id") == args.run_id]
    if not matches:
        sys.exit(f"找不到运行记录 {args.run_id}；先 lab sync 或 git pull 再试。")
    path, record = matches[0]
    record.update(status=args.status, ended=dt.datetime.now().isoformat(timespec="seconds"))
    if args.note:
        record["note"] = f"{record.get('note') or ''} {args.note}".strip()
    if args.outputs:
        record["outputs"] = args.outputs
    write_json(path, record)
    commit_and_push(top, f"run[{current_machine()}]({record.get('exp', '?')}): end {args.run_id} {args.status}",
                    [path], push=not args.no_push)
    return 0


# ---------- reading the shared record ----------

def journal_lines(top: Path, days: int, machine: str | None) -> list[str]:
    # Unix timestamps shown in this machine's local time: commits from other machines carry their own
    # time zones, and old git (1.8) has no --date=iso-local.
    out = git(top, "log", f"--since={days}.days", "--format=%at%x09%s").stdout.splitlines()
    rows = []
    for line in out:
        stamp, _, subject = line.partition("\t")
        date = dt.datetime.fromtimestamp(int(stamp)).strftime("%Y-%m-%d %H:%M")
        match = COMMIT_SUBJECT.match(subject)
        who = (match.group("machine") if match else None) or "?"
        if machine and who != machine:
            continue
        rows.append(f"{date}  {who:<8} {subject}")
    return rows


def run_line(r: dict) -> str:
    return (f"{r.get('status', '?'):<9} {r.get('machine', '?'):<8} {r.get('run_id')}  "
            f"{r.get('job') or ''}  {r.get('run_dir', '')}")


def cmd_sync(args: argparse.Namespace) -> int:
    top = find_root(args)
    remotes = git(top, "remote").stdout.split()
    if not remotes:
        sys.exit("没有配置远程仓库。")
    if not rebase_onto_remote(top, remotes[0]):
        return 1
    return 0 if push_head(top) else 1


def cmd_runs(args: argparse.Namespace) -> int:
    top = find_root(args)
    refresh(top, not args.no_pull)
    rows = [r for _, r in run_records(top)
            if (not args.active or r.get("status") == "running")
            and (not args.machine or r.get("machine") == args.machine)
            and (not args.exp or r.get("exp") == args.exp)]
    if not rows:
        print("没有符合条件的运行记录（其他机器的记录要先 lab sync 或 git pull 才能看到）。")
    for r in sorted(rows, key=lambda r: r.get("started") or ""):
        print(run_line(r) + f"  {r.get('exp', '?')}")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    top = find_root(args)
    text = " ".join(args.text).strip()
    if not text:
        sys.exit("请写下做了什么、产物在哪。")
    commit_and_push(top, f"log[{current_machine()}]: {text}", [], push=not args.no_push)
    return 0


def cmd_journal(args: argparse.Namespace) -> int:
    top = find_root(args)
    refresh(top, not args.no_pull)
    rows = journal_lines(top, args.days, args.machine)
    print("\n".join(rows) if rows else f"最近 {args.days} 天没有记录（其他机器的记录要先 lab sync 或 git pull）。")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    top = find_root(args)
    refresh(top, not args.no_pull)
    print(f"仓库：{top} · 本机：{current_machine()}")
    active = [r for _, r in run_records(top) if r.get("status") == "running"]
    print("正在进行的运行：" + ("无" if not active else ""))
    for r in active:
        print("  " + run_line(r))
    print("最近记录：")
    for row in journal_lines(top, 7, None)[:5] or ["（最近 7 天没有）"]:
        print("  " + row)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lab", description="多机共享记录：谁在哪台机器上跑了什么")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="项目仓库路径（默认：当前目录所在的 git 仓库，其次是总台）")
    common.add_argument("--hub", action="store_true", help="使用总台仓库")
    pull = argparse.ArgumentParser(add_help=False)
    pull.add_argument("--no-pull", action="store_true", help="不先 git pull")
    push = argparse.ArgumentParser(add_help=False)
    push.add_argument("--no-push", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", parents=[common, pull], help="本机、正在进行的运行、最近记录")
    sub.add_parser("sync", parents=[common], help="拉取其他机器的提交（rebase）并推送本机提交")
    p_run = sub.add_parser("run", help="记录一次运行：在执行机器上 start，结束后 end")
    run_sub = p_run.add_subparsers(dest="run_command", required=True)
    p_start = run_sub.add_parser("start", parents=[common, push], help="快照已提交的代码，写运行记录并提交",
                                 epilog="用法：lab run start <exp-id> -- <命令>（命令只记录，不执行）")
    p_start.add_argument("exp", help="实验编号，例如 E1 或 2026-11-20-sd15-controlnet")
    p_start.add_argument("--job", help="Slurm 作业号或 tmux 会话名")
    p_start.add_argument("--note")
    p_end = run_sub.add_parser("end", parents=[common, push], help="标记运行结束并提交")
    p_end.add_argument("run_id")
    p_end.add_argument("--status", required=True, choices=RUN_STATUSES[1:])
    p_end.add_argument("--outputs", help="大产物所在位置（留在执行机器上）")
    p_end.add_argument("--note")
    p_runs = sub.add_parser("runs", parents=[common, pull], help="列出运行记录")
    p_runs.add_argument("--active", action="store_true", help="只看正在进行的")
    p_runs.add_argument("--machine")
    p_runs.add_argument("--exp")
    p_log = sub.add_parser("log", parents=[common, push], help="为零散工作留痕：生成一个带机器前缀的空提交")
    p_log.add_argument("text", nargs="+")
    p_journal = sub.add_parser("journal", parents=[common, pull], help="按时间列出各机器上的提交")
    p_journal.add_argument("--days", type=int, default=7)
    p_journal.add_argument("--machine")
    argv = list(sys.argv[1:] if argv is None else argv)
    tail: list[str] = []
    if "--" in argv:
        cut = argv.index("--")
        argv, tail = argv[:cut], argv[cut + 1:]
    args = parser.parse_args(argv)
    args.cmd = tail
    if args.command == "run":
        return {"start": cmd_run_start, "end": cmd_run_end}[args.run_command](args)
    return {"status": cmd_status, "sync": cmd_sync, "runs": cmd_runs, "log": cmd_log,
            "journal": cmd_journal}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
