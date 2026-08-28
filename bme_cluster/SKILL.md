---
name: bme-cluster
description: Prepare, submit, monitor, and debug Slurm CPU/GPU jobs for the BME cluster while enforcing its node, network, storage, and per-user resource limits.
---

# BME Cluster

Use this workflow for BME-cluster work.

## Establish the execution context

1. Treat a shell with `SLURM_JOB_ID` as a compute-node context. It has no network access.
2. Treat `10.15.49.6` and `10.15.49.7` as login nodes. Do not run training, inference, GPU work, or other compute-intensive workloads there. Use them only for environment setup, package installation, and downloads.
3. Treat `10.15.49.36` as the file-transfer node. Use it for large file transfers.
4. When the host cannot be identified, ask before initiating a costly or network-dependent operation.

## Work safely across the nodes

- Perform package installation, model/data downloads, and environment setup only on login nodes.
- Before submitting a job, ensure its environment, packages, models, and input data already exist on cluster storage. Never put `pip install`, `conda install`, `wget`, `curl`, `git clone`, or remote model/data downloads in a batch script.
- Use `/public_bme/home/maxquan/` as the project root: create projects, environments, logs, checkpoints, outputs, and other working files there.
- Put large datasets only in `/public_bme/home/maxquan/Datasets/`. Reference this directory from projects; do not copy datasets into individual project directories unless explicitly requested.
- `/public_bme2` is full: do not create, download, write, cache, log, checkpoint, or place temporary files anywhere under it. Do not select it as a fallback output or scratch location; use the `/public_bme/home/maxquan/` locations above instead.
- Keep `/home_data/home/quanmx` (`~`) limited to essential configuration, including shell, SSH, Conda, and Codex configuration. Do not create or place project code, datasets, logs, checkpoints, outputs, or virtual environments there.
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
6. Generate a copy with `scripts/new-gpu-job.sh` when appropriate, review it, then submit with `sbatch <script>.sh` only when asked to submit.
7. Monitor with `squeue`, inspect with `scontrol show job <job-id>`, and cancel with `scancel <job-id>` only when asked.

## Create and submit CPU jobs

1. Start from [assets/cpu-job-template.sh](assets/cpu-job-template.sh). Use `#SBATCH -p bme_cpu` and do not add `--gres`.
2. `-n 8`, `--mem=32G`, and `-t 96:00:00` are conservative defaults, not CPU-queue limits. Adjust them when the user specifies requirements, and inspect `sinfo` before submitting.
3. Generate a copy with `bash scripts/new-cpu-job.sh` when appropriate, review it, then submit with `sbatch <script>.sh` only when asked.

## Diagnose failures

- Check the `.out` log and `scontrol show job <job-id>` first.
- For pending jobs, check queue and node availability with `squeue`, `pestat`, and `sinfo`; only then recommend a justified `-w` choice.
- For download/import failures inside a job, move that setup step to a login node and resubmit after staging the artifacts.
- For live loss/metrics, prefer TensorBoard, a logger, or an explicitly flushed text file; Slurm `.out` output can be delayed.
- Do not leave a shell line-continuation backslash immediately before a commented-out command: it comments out the continuation rather than cleanly omitting an argument. Remove the backslash when disabling the last argument.
