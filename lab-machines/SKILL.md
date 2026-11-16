---
name: lab-machines
description: "Coordinate research work across the user's three machines: a MacBook (orchestration only), a Windows PC with WSL2 (data hub, RTX 3060) and the BME Slurm cluster. Decide where an experiment or download runs, announce machine/directory/command before any automated execution, keep one shared git record of runs and ad-hoc work (lab.py run/log/journal), and move large files without routing them through the Mac. Use whenever work involves running, downloading, syncing or locating data across these machines, or when the user asks what was done where. Use bme-cluster for Slurm specifics."
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

## Rules

1. **Know where you are.** Read `~/.config/lab/machine` (`mac`, `pc` or `cluster`). If it is missing, ask; never guess.
2. **Announce before executing.** Before any automated execution, such as a run, download, install, sync or deletion, tell the user in one line: machine / directory / command / expected time and GPU memory / data read and written. Then wait for confirmation. This applies even when you run on the machine you are on.
3. **Route by need.** No GPU and ≤5 minutes → `mac`. Fits the PC's free VRAM and time → `pc`. Otherwise → `cluster`. Prefer the machine that already has the data. Never download data or weights to the Mac.
4. **One shared record.** The research workspace (the topic repo with `lab.toml` and `tools/lab.py`, cloned on all three machines) is the source of truth for work done inside it. In any other research project, follow that repository's own `AGENTS.md`: do not switch to the workspace to initialize, and do not use `lab.py`; rules 2, 3, 5, 6 and 7 still apply there. Inside the workspace:
   - Start every session with `git pull`, then `tools/lab.py status`.
   - Register formal runs with `tools/lab.py run start topics/<id> --exp E1 -- <command>`, and close them with `tools/lab.py run end <run-id> --status done|failed --outputs <where large outputs are>`.
   - Record ad-hoc work (downloads, env setup, cleanup) with `tools/lab.py log "<what, where the outputs are>"`.
   - End every session with a commit and `tools/lab.py sync`. It rebases onto other machines' commits and pushes; lab.py also does this automatically when a push is rejected, and stops cleanly on conflicts.
   - Answer "what did I do where" with `tools/lab.py journal --days N` and `tools/lab.py runs`. Both pull first.
   - Each machine has a `lab` shell command that runs its own copy of `tools/lab.py` from anywhere, installed by `scripts/install_lab_command.sh <repo> <python>`. Its path arguments are relative to the workspace root.
5. **Assets are registered.** Every dataset or weight downloaded or moved goes into the workspace's `MACHINES.md` asset table, with source/revision, machine:path and size. Reuse before downloading, and never duplicate large files.
6. **Large files bypass the Mac.** Each machine downloads what it needs from the mirror. PC↔cluster transfers go through the cluster transfer node. Only small results and figures travel through git.
7. **Respect existing constraints.** Follow bme-cluster for anything on the cluster. On the PC, check free VRAM first, because a Zotero translation model shares the GPU. Do not stop it without permission.

## Run on a remote machine from the Mac

1. Commit and push the code from the Mac.
2. On the target machine, run `git pull`, then `lab.py run start …`. lab.py snapshots the committed topic code into that machine's `runs_root`.
3. Launch in tmux (`pc`) or with sbatch (`cluster`), and add the tmux session name or job ID with `--job`.
4. When it finishes, copy small metrics and figures into the topic's `results/` and `figures/`, run `lab.py run end`, then commit and push.
5. Back on the Mac, `git pull` shows everything.

Use `ssh pc '<cmd>'` and `ssh bme_login2 '<cmd>'` for short non-interactive commands. Never run long processes through a bare SSH session: use tmux or Slurm, so closing the Mac does not kill them.

## Guardrails

- Never type passwords or sudo for the user. Hand over the exact command for them to run.
- Do not delete, move or overwrite existing data, weights or old project outputs unless asked. Migrations copy first, verify hashes, and leave the original for the user to delete.
- The repo stores only code, docs, small metrics and figures. Large outputs stay on the machine that produced them, with their path recorded.
