#!/usr/bin/env python3
"""Research project template tool: init a project, open an experiment card, check the project.

Standard library only. Git is called with cwd instead of `git -C` so old git versions work.
"""
import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parent.parent / "assets" / "template"
PLACEHOLDER = "【待填"
TYPES = ("trunk", "ablation", "analysis", "spike")
LINE_LIMITS = {
    "AGENTS.md": 80, "CLAUDE.md": 10, "STATE.md": 40, "README.md": 80,
    "docs/PROJECT.md": 150, "docs/DATA.md": 150, "docs/PIPELINE.md": 120, "docs/DECISIONS.md": 200,
}
CARD_LINES = 40
MAX_QUEUE = 5
MAX_FIGURES = 4
MAX_TRACKED_KB = 1024
ALLOWED_MD = set(LINE_LIMITS) | {"EXPERIMENTS.md"}
SKIP_MD_PREFIXES = ("scratch/", "runs/", "third_party/")
CODE_DIRS = ("src", "configs", "tests")
CARD = """# {id}

类型：{type}　状态：queued

## 问题
【待填：一句话，能用一个数或一张图回答】

## 影响的决定
- 【待填：结果 A】：下一步做什么。
- 【待填：结果 B】：下一步做什么。

## 预测
【待填：方向和大致幅度】

## 推翻条件
【待填：看到什么结果就承认预测错了】

## 相对主干的改动
【待填：只有一处，写 configs/exp/{id}.yaml 改了什么】

## 评测
同 PIPELINE.md。

## 预算和停止门槛
【待填：时间或 GPU 小时；达到什么就停】

## 要保存的产物
result.json；【待填：图和 runs/ 下保留的文件】

## 结果
【运行后填写：数字、与主干的差、结论、这个实验不能说明什么】
"""


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    return result.returncode, result.stdout


def find_root(start):
    path = Path(start).resolve()
    for candidate in (path, *path.parents):
        if (candidate / "STATE.md").is_file() and (candidate / "EXPERIMENTS.md").is_file():
            return candidate
    sys.exit("找不到项目根目录：需要同时有 STATE.md 和 EXPERIMENTS.md。新项目先运行 init。")


def lines_of(path):
    return path.read_text(encoding="utf-8").splitlines()


def cmd_init(args):
    if not TEMPLATE.is_dir():
        sys.exit("init 需要从 skill 的 scripts/project.py 运行，项目里的 tools/project.py 不带模板。")
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", args.name):
        sys.exit("--name 必须是合法的 Python 包名（小写字母、数字、下划线）。")
    root = Path(args.dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    today = args.date or datetime.date.today().isoformat()
    created, skipped = [], []
    for source in sorted(TEMPLATE.rglob("*")):
        if source.is_dir():
            continue
        relative = source.relative_to(TEMPLATE).as_posix().replace("__PKG__", args.name)
        if relative == "gitignore":
            relative = ".gitignore"
        target = root / relative
        if target.exists():
            skipped.append(relative)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8")
        for key, value in (("{{PKG}}", args.name), ("{{NAME}}", args.title or args.name), ("{{DATE}}", today)):
            text = text.replace(key, value)
        target.write_text(text, encoding="utf-8")
        created.append(relative)
    tool = root / "tools" / "project.py"
    if tool.exists():
        skipped.append("tools/project.py")
    else:
        tool.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(HERE), str(tool))
        created.append("tools/project.py")
    for name in ("runs", "scratch"):
        (root / name).mkdir(exist_ok=True)
    if git(root, "rev-parse", "--is-inside-work-tree")[0] != 0:
        git(root, "init")
        print("已运行 git init。")
    print("创建 {} 个文件，跳过 {} 个已存在的文件。".format(len(created), len(skipped)))
    for relative in skipped:
        print("  跳过：" + relative)
    print("下一步：填写 docs/ 和 STATE.md 里的【待填】，然后提交。")


def cmd_new(args):
    root = find_root(args.root)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.slug):
        sys.exit("slug 只能用小写字母、数字和连字符。")
    exp_id = "{}-{}".format(args.date or datetime.date.today().isoformat(), args.slug)
    directory = root / "experiments" / exp_id
    if directory.exists():
        sys.exit("已存在：experiments/" + exp_id)
    directory.mkdir(parents=True)
    (directory / "CARD.md").write_text(CARD.format(id=exp_id, type=args.type), encoding="utf-8")
    row = "| {id} | {type} | 【待填】 | 【待填】 | queued | 【待填】 | [卡片](experiments/{id}/CARD.md) |\n".format(
        id=exp_id, type=args.type)
    registry = root / "EXPERIMENTS.md"
    text = registry.read_text(encoding="utf-8")
    registry.write_text(text + ("" if text.endswith("\n") else "\n") + row, encoding="utf-8")
    print("已创建 experiments/{}/CARD.md，并在 EXPERIMENTS.md 追加一行。".format(exp_id))
    print("下一步：填写卡片，交给用户批准后提交 exp({}): card。".format(exp_id))


def registry_rows(root):
    rows = {}
    for line in lines_of(root / "EXPERIMENTS.md"):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 7 and cells[0] not in ("id", "") and not set(cells[0]) <= set("-: "):
            rows[cells[0]] = cells
    return rows


def section(lines, title):
    body, inside = [], False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:].strip().startswith(title)
            continue
        if inside:
            body.append(line)
    return body


def cmd_check(args):
    root = find_root(args.root)
    errors, warnings = [], []
    in_git = git(root, "rev-parse", "--is-inside-work-tree")[0] == 0
    if in_git:
        files = git(root, "ls-files")[1].splitlines()
        files += git(root, "ls-files", "--others", "--exclude-standard")[1].splitlines()
    else:
        errors.append("项目不在 git 仓库里。")
        files = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    files = sorted({f for f in files if (root / f).is_file()})

    for relative, limit in LINE_LIMITS.items():
        path = root / relative
        if path.is_file() and len(lines_of(path)) > limit:
            errors.append("{} 有 {} 行，上限 {} 行：合并或删减。".format(relative, len(lines_of(path)), limit))
    for relative in files:
        if not relative.endswith(".md") or relative.startswith(SKIP_MD_PREFIXES):
            continue
        if re.fullmatch(r"experiments/[^/]+/CARD\.md", relative):
            if len(lines_of(root / relative)) > CARD_LINES:
                errors.append("{} 超过 {} 行。".format(relative, CARD_LINES))
        elif relative not in ALLOWED_MD:
            errors.append("多余的 Markdown 文件：{}。内容并入已有文件，或先问用户。".format(relative))

    if in_git:
        dirty = git(root, "status", "--porcelain", "--", *CODE_DIRS)[1].splitlines()
        if dirty:
            errors.append("{} 下有 {} 个未提交或未跟踪的文件，正式运行前先提交。例如：{}".format(
                "、".join(CODE_DIRS), len(dirty), dirty[0].strip()))
        for relative in git(root, "ls-files")[1].splitlines():
            path = root / relative
            if path.is_file() and path.stat().st_size > MAX_TRACKED_KB * 1024:
                errors.append("git 里有超过 {} KB 的文件：{}。".format(MAX_TRACKED_KB, relative))

    state = lines_of(root / "STATE.md")
    trunk = "\n".join(section(state, "当前主干"))
    match = re.search(r"commit[:：]\s*`?([0-9a-f]{7,40})\b", trunk)
    if match is None:
        warnings.append("STATE.md 还没有写主干的 commit：主干未锁定，此时只做 trunk 类型的实验。")
    elif in_git and git(root, "cat-file", "-e", match.group(1) + "^{commit}")[0] != 0:
        errors.append("STATE.md 里的主干 commit {} 不存在。".format(match.group(1)))
    if PLACEHOLDER in "\n".join(section(state, "当前唯一问题")):
        warnings.append("STATE.md 没有写当前唯一问题。")
    queued = [line for line in section(state, "排队") if re.match(r"\s*(-|\d+\.)\s+\S", line)]
    if len(queued) > MAX_QUEUE:
        errors.append("STATE.md 排队有 {} 项，上限 {} 项。".format(len(queued), MAX_QUEUE))
    updated = re.search(r"更新[:：]\s*(\d{4}-\d{2}-\d{2})", "\n".join(state))
    if updated is None:
        errors.append("STATE.md 缺少“更新：YYYY-MM-DD”。")
    elif in_git:
        last = git(root, "log", "-1", "--format=%cd", "--date=short")[1].strip()
        if last and updated.group(1) < last:
            warnings.append("STATE.md 更新于 {}，早于最近一次提交 {}：确认它没有过期。".format(updated.group(1), last))

    rows = registry_rows(root)
    experiments = root / "experiments"
    directories = sorted(p for p in experiments.iterdir() if p.is_dir()) if experiments.is_dir() else []
    for directory in directories:
        if not (directory / "CARD.md").is_file():
            errors.append("experiments/{} 没有 CARD.md。".format(directory.name))
        if directory.name not in rows:
            errors.append("experiments/{} 没有登记在 EXPERIMENTS.md。".format(directory.name))
        figures = [p for p in (directory / "figures").glob("*") if p.is_file()] if (directory / "figures").is_dir() else []
        if len(figures) > MAX_FIGURES:
            warnings.append("experiments/{} 有 {} 张图，上限 {} 张。".format(directory.name, len(figures), MAX_FIGURES))
        status = rows.get(directory.name, [""] * 7)[4]
        if status in ("done", "stopped") and not (directory / "result.json").is_file():
            errors.append("experiments/{} 状态是 {}，但没有 result.json。".format(directory.name, status))
    running = [key for key, cells in rows.items() if cells[4] == "running"]
    if len(running) > 1:
        warnings.append("有 {} 个实验同时是 running：{}。同一时间只回答一个问题。".format(len(running), "、".join(running)))

    for message in errors:
        print("ERROR " + message)
    for message in warnings:
        print("WARN  " + message)
    print("check：{} 个 ERROR，{} 个 WARN。".format(len(errors), len(warnings)))
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command")
    commands.required = True
    init = commands.add_parser("init", help="从模板创建项目，只创建缺失的文件")
    init.add_argument("dir")
    init.add_argument("--name", required=True, help="Python 包名，用于 src/<name>/")
    init.add_argument("--title", help="项目显示名，默认同 --name")
    init.add_argument("--date")
    init.set_defaults(run=cmd_init)
    new = commands.add_parser("new", help="新建实验卡片并登记")
    new.add_argument("slug")
    new.add_argument("--type", required=True, choices=TYPES)
    new.add_argument("--date")
    new.add_argument("--root", default=".")
    new.set_defaults(run=cmd_new)
    check = commands.add_parser("check", help="检查项目是否符合模板约定")
    check.add_argument("--root", default=".")
    check.set_defaults(run=cmd_check)
    args = parser.parse_args()
    sys.exit(args.run(args) or 0)


if __name__ == "__main__":
    main()
