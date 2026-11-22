---
name: lab-machines
description: "Coordinate research work across the user's three machines: a MacBook (orchestration only), a Windows PC with WSL2 (data hub, RTX 3060) and the BME Slurm cluster. Decide where an experiment or download runs, announce machine/directory/command before any automated execution, keep one shared git record of runs and ad-hoc work in any project repo (the `lab` command: run/log/journal/sync), and move large files without routing them through the Mac. Use whenever work involves running, downloading, syncing or locating data across these machines, or when the user asks what was done where. Use bme-cluster for Slurm specifics."
disable-model-invocation: true
---

# Lab Machines

The user works on three machines and has Codex installed on each, so it is easy to lose track of what happened where. Every action must answer three questions in a durable, shared place: **where** it ran, **what** ran, and **where the outputs are**.

## Machines

| ID | Role | Holds | Runs |
| --- | --- | --- | --- |
| `mac` | Orchestration | git checkouts, docs, small results and figures | Planning, coding, analysis; L0 and ≤5-minute CPU smoke tests. **No datasets, weights or caches.** |
| `pc` | Data hub + single-GPU workstation (WSL2 Ubuntu 24.04) | Hot data, caches and envs on WSL ext4 (`~/lab`); the existing weight library on D: | L1/L2: fits in the free part of the 12 GB RTX 3060 and finishes within hours |
| `cluster` | Large compute (BME Slurm) | `/public_bme/home/maxquan/{Datasets,Projects}` | L3: more VRAM, multi-GPU or long training, via [bme-cluster](../bme_cluster/SKILL.md) |

Exact hosts, paths and limits are in [references/machines.md](references/machines.md). Also read [pc-wsl](references/pc-wsl.md) before running on the PC, and [transfer](references/transfer.md) before moving data.

## Scope

These rules apply only when the user names this skill, or inside a repo whose own `AGENTS.md` opts in (the research-project template and the hub repo do). The user also uses Codex and Claude for unrelated work, so never write these rules into a global file such as `~/.codex/AGENTS.md` or `~/.claude/CLAUDE.md`. `scripts/remove_global_note.py <target>` removes a block left there by older installs.

## Rules

1. **Know where you are.** Read `~/.config/lab/machine` (`mac`, `pc` or `cluster`). If it is missing, ask; never guess.
2. **Announce before executing.** Before any automated execution, such as a run, download, install, sync or deletion, tell the user in one line: machine / directory / command / expected time and GPU memory / data read and written. Then wait for confirmation. This applies even when you run on the machine you are on.
3. **Route by need.** No GPU and ≤5 minutes → `mac`. Fits the PC's free VRAM and time → `pc`. Otherwise → `cluster`. Prefer the machine that already has the data. Never download data or weights to the Mac.
4. **One shared record.** Each git project repo (cloned on the machines that use it) is its own record, and the `lab` command (`scripts/lab.py`, installed on every machine) reads and writes it from any directory inside the repo. Outside any repo it uses the hub repo named in `~/.config/lab/hub`, which also holds `MACHINES.md`. The project's own `AGENTS.md` still wins on everything else.
   - Start every session with `lab status`. It pulls first and shows running jobs and the latest entries.
   - Register formal runs with `lab run start <exp-id> -- <command>` and close them with `lab run end <run-id> --status done|failed|cancelled --outputs <where large outputs are>`. `run start` refuses uncommitted or untracked non-Markdown files, snapshots `git archive HEAD` into `<project>/runs/<exp-id>/<run-id>/code` (in a shared repo, `<project>` is the sub-project holding `STATE.md` and `EXPERIMENTS.md` above the cwd, and only that sub-project is snapshotted) (set `LAB_RUNS_ROOT` to store runs elsewhere), and commits `.lab/runs/<run-id>.json`. The command is recorded, not executed.
   - Record ad-hoc work (downloads, env setup, cleanup) with `lab log "<what, where the outputs are>"`; `lab log --hub` writes to the hub even inside a project.
   - End every session with a commit and `lab sync`. It rebases onto other machines' commits and pushes; `lab` also does this automatically when a push is rejected, and stops cleanly on conflicts or a dirty tree.
   - Answer "what did I do where" with `lab journal --days N` and `lab runs [--active --machine --exp]`. Both pull first (`--no-pull` skips it).
   - `scripts/install_lab_command.sh <python> <hub_repo>` installs the `lab` command and writes the hub path; Commit subjects are `kind[machine](exp): text`.
5. **Assets are registered.** Every dataset or weight downloaded or moved goes into the hub's `MACHINES.md` asset table, with source/revision, machine:path and size. Before writing a data plan or any download, read that table and `ls` the target machine's dataset root (on the cluster `/public_bme/home/maxquan/Datasets/`): data can exist there unregistered, and if so register it. New datasets go to `$LAB_DATA_DIR/<name>/` and weights to `$LAB_MODELS_DIR`, both set in each machine's shell rc; never into a project directory. Reuse before downloading, and never duplicate large files.
6. **Large files bypass the Mac.** Each machine downloads what it needs from the mirror. PC↔cluster transfers go through the cluster transfer node. Only small results and figures travel through git.
7. **Respect existing constraints.** Follow bme-cluster for anything on the cluster. On the PC, check free VRAM first, because a Zotero translation model shares the GPU. Do not stop it without permission.
8. **Check storage and GPU memory when you need them; never trust recorded numbers.** [machines](references/machines.md) lists where each machine may write and records no free space, quota or VRAM figures, because they change. Before writing anything large (a download, cache, checkpoints or a copy), on the target machine: run `df -h <dir>` (it shows the whole filesystem, not your quota); on the cluster also run `quota -s` (empty output does not mean unlimited); create and delete an empty probe file in `<dir>`, since a full quota fails even when `df` shows free space; and compare with the expected size including caches and checkpoints. Before a GPU run, check free memory with `nvidia-smi`. Put what you measured into the rule-2 announcement. If space is short, say so and ask; never switch to another location on your own.

## Run on a remote machine from the Mac

1. Commit and push the code from the Mac (`lab sync`).
2. On the target machine, `git pull` in the project repo, then `lab run start <exp-id> -- <command>`. It snapshots the committed code into that machine's `runs/`.
3. Launch in tmux (`pc`) or with sbatch (`cluster`), and add the tmux session name or job ID with `--job`.
4. When it finishes, put small metrics and figures where the project's artifact contract says (`result.json`, figures), run `lab run end`, then commit and `lab sync`.
5. Back on the Mac, `lab status` or `lab journal` shows everything.

Use `ssh pc '<cmd>'` and `ssh bme_login2 '<cmd>'` for short non-interactive commands. On `pc`, a bare `ssh pc 'lab …'` does not find `lab` (zsh non-interactive PATH): call `~/.local/bin/lab` or `ssh pc 'bash -lc "lab …"'`. Never run long processes through a bare SSH session: use tmux or Slurm, so closing the Mac does not kill them.

## Guardrails

- Never type passwords or sudo for the user. Hand over the exact command for them to run.
- Do not delete, move or overwrite existing data, weights or old project outputs unless asked. Migrations copy first, verify hashes, and leave the original for the user to delete.
- Repos store only code, docs, small metrics and figures. Large outputs stay on the machine that produced them, with their path recorded.
