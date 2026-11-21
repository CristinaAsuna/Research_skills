---
name: bme-cluster
description: Develop locally and run experiments on the BME cluster through SSH and Slurm; stage code, environments, datasets and weights, submit and inspect CPU/GPU jobs, and retrieve results within cluster limits.
---

# BME Cluster

Use this workflow for BME-cluster work.

## Local Codex with remote execution

When invoked on the user's local machine, keep planning, code editing, and experiment analysis local. Use the existing SSH alias `bme_login1` for short remote commands, and Slurm for compute. A second remote Codex process is optional, not a dependency of this workflow.

Read [references/local-remote-workflow.md](references/local-remote-workflow.md) for SSH preflight, code snapshots, resumable downloads, submission records, status recovery, and selective result retrieval. Use this route when the user asks to code locally while using cluster GPUs, data or weights. Do not run the local Mac's project paths on Linux or copy its virtual environment to the cluster.

An instruction to implement and run an experiment authorizes the necessary staging and submission within the stated resource scope. An instruction to prepare a job only does not authorize submission. Preserve explicit resource and budget constraints; do not infer an unrestricted experiment sweep.

Login-process lifetime and Slurm job wall time are different constraints. Do not use `nohup`, `tmux`, a remote Codex daemon, or repeated relaunches to bypass the reported one-hour login-process limit. Use bounded, resumable login-node setup/download steps. Recheck actual Slurm limits before submission.

## Establish the execution context

1. Treat a shell with `SLURM_JOB_ID` as a compute-node context. It has no network access.
2. Treat `10.15.49.6` and `10.15.49.7` as login nodes. Do not run training, inference, GPU work, or other compute-intensive workloads there. Use them only for environment setup, package installation, and downloads.
3. Treat `10.15.49.36` as the file-transfer node. Use it for large file transfers.
4. When the host cannot be identified, ask before initiating a costly or network-dependent operation.

## Work safely across the nodes

- Perform package installation, model/data downloads, and environment setup only on login nodes.
- Before submitting a job, ensure its environment, packages, models, and input data already exist on cluster storage. Never put `pip install`, `conda install`, `wget`, `curl`, `git clone`, or remote model/data downloads in a batch script.
- **Three work roots, chosen by measured space.** Project research (code, environments, logs, checkpoints, outputs) may live in any of `/public_bme/home/maxquan/`, `/public_bme2/bme-cuizhm/maxquan/` (the group's shared volume) and `/public/home/quanmx/`. They are separate filesystems that fill up independently, so record no capacity numbers. Before creating a project or writing anything large, check each candidate root on the login node: `df -h <root>` (whole filesystem, not your quota), `quota -s` (empty output does not mean unlimited), and an empty probe file created and deleted in the root (a full quota fails even when `df` shows space); then compare with the expected size including caches and checkpoints. Keep an existing project in the root it already lives in. Otherwise pick a root with room, and put the choice and the numbers you measured into the announcement. If no root has room, stop and ask; never delete data to make space.
- **Shared assets stay in one place, whatever root a project uses.** Datasets go in `/public_bme/home/maxquan/Datasets/` and pretrained weights in `/public_bme/home/maxquan/Datasets/models/` (`LAB_MODELS_DIR`). Reference them from projects; do not copy datasets or weights into a project unless explicitly requested. If `/public_bme` has no room for a new dataset or weight, ask where it should go.
- **Home needs the user's permission.** `/home_data/home/quanmx` (`~`) holds global configuration and tools: shell, SSH, conda, Codex, installed skills, the `lab` command. Ask before writing anything there, and never put project code, datasets, logs, checkpoints, outputs or project environments there.
- `/tmp` is login-node scratch only; compute nodes cannot see it.
- Read [references/cluster-guide.md](references/cluster-guide.md) for the source facts and queue limits.

## Choose resources and enforce limits

- The available partitions are `bme_gpu`, `bme_a10080g`, `bme_gpupub`, and `bme_cpu`.
- Before submitting, inspect the user's `PENDING` and `RUNNING` jobs in all four partitions with `squeue`. There may be at most two such jobs in total. Do not submit a third job.
- For GPU work, use `scontrol show job <job-id>` as needed to determine existing requested GPUs. Across `bme_gpu`, `bme_a10080g`, and `bme_gpupub`, the user's requested GPUs may total at most three. `bme_cpu` consumes a job slot but no GPU allocation.
- Apply each partition's GPU limit to the user's total concurrent/pending requests: `bme_gpu` up to two GPUs, `bme_a10080g` up to one A100 80 GB GPU, and `bme_gpupub` up to one V100 GPU.
- Select among compatible partitions to minimize expected time to usable resources. Compare `squeue`, `pestat`, and `sinfo`, and use `squeue --start` when its estimate is available. Do not prefer a free partition merely because it is free.
- Inspect availability by exact GPU GRES type, not only by GPU family. Use `pestat` or `sinfo -O Nodehost,Gres:.30,GresUsed:.45` to compare compatible variants before choosing `--gres`. For example, when a workload accepts either V100 interconnect, compare `TeslaV100S-PCIE-32GB` and `TeslaV100-SXM2-32GB` and request the variant with usable capacity expected soonest. Only pin PCIe or SXM2 when the user or workload requires that topology.
- If a compatible free partition is occupied, constrained by the user's allocation, or expected to wait longer, use a compatible alternative. For example, submit a one-V100 job to `bme_gpu` rather than waiting behind `bme_gpupub`.
- Never change the requested GPU type, GPU memory class, GPU count, or a GPU job into a CPU job unless the user says the workload is compatible with that alternative. When the request allows several resource types, choose the compatible option expected to start soonest.
- Do not cancel, move, or duplicate an existing job unless asked.

## Create and submit GPU jobs

1. Start from [assets/gpu-job-template.sh](assets/gpu-job-template.sh); retain `-n 8` unless the user explicitly understands the I/O trade-off.
2. Always request an allowed GPU type with `#SBATCH --gres=gpu:<GPU_TYPE>:<COUNT>`. Check the exact queue-to-GPU mapping in [references/cluster-guide.md](references/cluster-guide.md), including the one-GPU limit of free queues. Do not select `bme_unlimited` solely because it appears in an older permissions list: the provided tutorial does not document its hardware or limits.
3. Follow the resource-selection and quota checks above. Treat `squeue --start` only as an estimate, not a guarantee.
4. Leave the `-w` directive out unless a particular GPU/node is necessary. Inspect `pestat` or `sinfo -O Nodehost,Gres:.30,GresUsed:.45` first when a specific node, 80 GB GPU, or multiple GPUs are required.
5. Set a distinct job name, output-log path, memory, wall time, conda environment, and command. Keep wall time at or below `120:00:00`.
6. Generate a copy with `scripts/new-gpu-job.sh` when appropriate, review it, create the output/error directories relative to the submission working directory, and submit with `sbatch <script>.sh` when submission is within the user's request. For local orchestration, record a unique run ID and remote job ID as described in the remote workflow.
7. Monitor with `squeue`, inspect with `scontrol show job <job-id>`, and cancel with `scancel <job-id>` only when asked.

## Create and submit CPU jobs

1. Start from [assets/cpu-job-template.sh](assets/cpu-job-template.sh). Use `#SBATCH -p bme_cpu` and do not add `--gres`.
2. `-n 8`, `--mem=32G`, and `-t 96:00:00` are conservative defaults, not CPU-queue limits. Adjust them when the user specifies requirements, and inspect `sinfo` before submitting.
3. Generate a copy with `bash scripts/new-cpu-job.sh` when appropriate, review it, ensure log directories exist, then submit with `sbatch <script>.sh` when submission is within the user's request.

## Diagnose failures

- Check the `.out` log and `scontrol show job <job-id>` first.
- A job disappearing from `squeue` does not prove success. Check `sacct` state and exit codes, application logs, and the expected artifacts. If accounting is unavailable, state that limitation rather than assuming completion.
- For pending jobs, check queue and node availability with `squeue`, `pestat`, and `sinfo`; only then recommend a justified `-w` choice.
- For download/import failures inside a job, move that setup step to a login node and resubmit after staging the artifacts.
- For live loss/metrics, prefer TensorBoard, a logger, or an explicitly flushed text file; Slurm `.out` output can be delayed.
- Do not leave a shell line-continuation backslash immediately before a commented-out command: it comments out the continuation rather than cleanly omitting an argument. Remove the backslash when disabling the last argument.
