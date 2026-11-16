---
name: research-project
description: "Set up and run a long-lived research project that coding agents execute, so the work stays on its trunk: one short STATE.md naming the current trunk and the single open question, experiment cards approved before any experiment code, one evaluation entry point, a fixed artifact contract, and a step-by-step procedure for migrating the trunk (moving a messy old project into the template, or promoting an experiment to the new trunk). Use when the user starts a new research codebase, wants to tidy or migrate an existing one, opens, queues or closes an experiment or ablation in a project that has STATE.md and EXPERIMENTS.md, or complains that agents run redundant experiments, drift from the main line or pile up caches and outputs. Not for replaying a paper's discovery with toy experiments (use research-discovery-lab) or for choosing which machine runs a job (use lab-machines)."
---

# Research Project

Keep a research project legible to a fresh agent session and to the user: what the trunk is, which single question is open, and where every result lives. Default to Chinese for discussion and documents; code and file names stay English.

A project is the nearest directory (cwd or a parent) containing both `STATE.md` and `EXPERIMENTS.md`. Its `AGENTS.md` holds the binding rules and overrides this skill's defaults. Read `AGENTS.md`, then `STATE.md`, then the one card `STATE.md` points to. Do not read `runs/`, `scratch/` or other experiments unless the task needs them.

Project tool: `<python> tools/project.py new <slug> --type trunk|ablation|analysis|spike | check`. It needs only the standard library and git.

## Pick the action

| Request | Do | Read first |
| --- | --- | --- |
| Start a new project | `<python> scripts/project.py init <dir> --name <package>`; then fill `docs/` and `STATE.md` with the user | — |
| Open, run or close an experiment | Write the card, get approval, run, record | [experiments](references/experiments.md) |
| Move an old project into the template, or replace the trunk | Follow the procedure step by step | [trunk-migration](references/trunk-migration.md) |
| Session end, or "is the project in order?" | `tools/project.py check`, fix errors, commit | — |

`init` only creates missing files and never overwrites; it runs `git init` when the directory is not in a repository.

## Working rules

1. **One trunk, one question.** `STATE.md` names the trunk (tag, commit, config, evaluation set, headline metric, checkpoint) and exactly one open question. If the trunk cannot be named, the first task is to produce and lock one number, not to explore.
2. **Card before code.** No experiment code and no runs without a card the user approved. A card states what each outcome would change; if both outcomes lead to the same next step, do not run it. Ideas that come up while working go to the parked list in `STATE.md`.
3. **Trunk plus one difference.** An experiment is `configs/exp/<id>.yaml` over `configs/trunk.yaml`. Do not create a package per experiment, and never import one experiment from another.
4. **One evaluation entry.** Every result comes from the command and evaluation set in `docs/PIPELINE.md`. Changing either is a decision recorded in `docs/DECISIONS.md`.
5. **Artifacts have one home.** Git holds code, configs, docs, cards, `result.json` and at most 4 figures per experiment. Checkpoints, caches and logs live in `runs/<id>/`: best checkpoint only (plus last while training), one copy of any cache, one format per result. Throwaway files go to `scratch/`.
6. **Commit before formal runs** and record the commit in `result.json`. End every session by updating `STATE.md` and the experiment's row, running `check`, committing and pushing.
7. **Merge, do not append.** The Markdown file set is fixed and line-capped. Rewrite existing entries; no diaries, no new Markdown files.
8. **Delegate reading, keep judgment.** Use subagents to read logs, aggregate metrics, search code or read papers, returning conclusions with paths. Experiment design, trunk decisions and document edits stay in the main session.

## Guardrails

- Announce machine / directory / command / expected time and GPU memory / data read and written before any run, download, install, sync or deletion, and wait for confirmation. Route work with `lab-machines` and `bme-cluster`.
- Never delete, move or overwrite existing data, weights or `runs/` without the user's item-by-item approval. Migrations copy; the old project stays read-only.
- Do not tune, pick seeds or change metrics to reach a predicted result. Report failed and stopped experiments as such.
- Change `configs/trunk.yaml` or the trunk section of `STATE.md` only through a trunk migration.
