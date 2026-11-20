---
name: research-project
description: "Set up and run a long-lived research project that coding agents execute, so the work stays on its trunk: one short STATE.md naming the current trunk and the single open question, experiment cards approved before any experiment code, one evaluation entry point, a fixed artifact contract, and a step-by-step procedure for migrating the trunk (moving a messy old project into the template, or promoting an experiment to the new trunk). Use when the user starts a new research codebase, wants to tidy or migrate an existing one, opens, queues or closes an experiment or ablation in a project that has STATE.md and EXPERIMENTS.md, or complains that agents run redundant experiments, drift from the main line or pile up caches and outputs. Not for choosing which machine runs a job or for the shared run record (use lab-machines)."
---

# Research Project

Keep a research project legible to a fresh agent session and to the user: what the trunk is, which single question is open, and where every result lives. Default to Chinese for discussion and documents; code and file names stay English.

A project is the nearest directory (cwd or a parent) containing both `STATE.md` and `EXPERIMENTS.md`. Its `AGENTS.md` holds the binding rules and overrides this skill's defaults. Read `AGENTS.md`, then `STATE.md`, then the one card `STATE.md` points to. Do not read `runs/`, `scratch/` or other experiments unless the task needs them.

Project tool: `<python> tools/project.py new <slug> --type trunk|ablation|analysis|spike | check | audit [--exp <id>] | prune <list> [--yes]`. It needs only the standard library and git.

## Pick the action

| Request | Do | Read first |
| --- | --- | --- |
| Start a new project | `<python> scripts/project.py init <dir> --name <package>`; then fill `docs/` and `STATE.md` with the user | — |
| Open, run or close an experiment | Write the card, get approval, run, record | [experiments](references/experiments.md) |
| The user brings their own experiment or method design | Review it with the §7 checklist (questions and feasibility only, never swap in your own design), then write it up as a card | [experiments](references/experiments.md) §7 |
| Move an old project into the template, or replace the trunk | Follow the procedure step by step | [trunk-migration](references/trunk-migration.md) |
| Session end, or "is the project in order?" | `tools/project.py check`, fix errors, commit | — |

`init` only creates missing files and never overwrites; it runs `git init` when the directory is not in a repository.

## Working rules

1. **One trunk, one question.** `STATE.md` names the trunk (tag, commit, config, evaluation set, headline metric, checkpoint) and exactly one open question. If the trunk cannot be named, the first task is to produce and lock one number, not to explore.
2. **Card before code.** No experiment code and no runs without a card the user approved. A card states what each outcome would change; if both outcomes lead to the same next step, do not run it. Ideas that come up while working go to the parked list in `STATE.md`.
3. **Trunk plus one difference.** An experiment is `configs/exp/<id>.yaml` over `configs/trunk.yaml`. Do not create a package per experiment, and never import one experiment from another.
4. **One evaluation entry.** Every result comes from the command and evaluation set in `docs/PIPELINE.md`. Changing either is a decision recorded in `docs/DECISIONS.md`.
5. **Artifacts have one home, enforced by code.** Git holds code, configs, docs, cards, `result.json` and at most 4 figures per experiment. Checkpoints and caches are written only through `src/<pkg>/artifacts.py` (`save_checkpoint` keeps best.pt and last.pt; `cache_dir` keys one copy per cache; smoke runs go to `scratch/`), every run starts with `source tools/env.sh` so tool caches land in a temp dir, and when an experiment is done or stopped, `tools/project.py audit --exp <id>` writes a removal list that is pruned only after the user approves it.
6. **Commit before formal runs**, register them with `lab run start <exp-id> -- <command>` (lab-machines) and record the commit and run id in `result.json`. End every session by updating `STATE.md` and the experiment's row, running `check`, committing and `lab sync`.
7. **Merge, do not append.** The Markdown file set is fixed and line-capped. Rewrite existing entries; no diaries, no new Markdown files.
8. **Delegate reading, keep judgment.** Use subagents to read logs, aggregate metrics, search code or read papers, returning conclusions with paths. Experiment design, trunk decisions and document edits stay in the main session.

## Guardrails

- Announce machine / directory / command / expected time and GPU memory / data read and written before any run, download, install, sync or deletion, and wait for confirmation. Route work with `lab-machines` and `bme-cluster`.
- Never delete, move or overwrite existing data, weights or `runs/` without the user's item-by-item approval. Migrations copy; the old project stays read-only.
- Do not tune, pick seeds or change metrics to reach a predicted result. Report failed and stopped experiments as such.
- Change `configs/trunk.yaml` or the trunk section of `STATE.md` only through a trunk migration.
