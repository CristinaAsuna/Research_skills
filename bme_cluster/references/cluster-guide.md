# BME cluster reference

Source: user-provided “BME Cluster Tutorial”, last updated 2025-11-02.

## Access and roles

| Role | Host | Rule |
| --- | --- | --- |
| Login node | `10.15.49.6:22112`, `10.15.49.7:22112` | Networked. Do not run training, inference, GPU work, or other compute-intensive workloads. Use for environment configuration, package installation, and downloads. |
| File-transfer node | `10.15.49.36:22112` | Use for large file transfers, e.g. via WinSCP. |
| Compute node | Allocated through Slurm | No network: prepare all dependencies, models, and data before submitting. |

## Storage

| Location | Use |
| --- | --- |
| `/home_data/home/quanmx` (`~`) | Global configuration and tools only (shell, SSH, conda, Codex, installed skills, `lab`). Writing here needs the user's permission. No project code, datasets, logs, checkpoints, outputs or project environments. |
| `/public_bme/home/maxquan/` | Work root 1: projects, environments, logs, checkpoints, outputs. |
| `/public_bme2/bme-cuizhm/maxquan/` | Work root 2, on the research group's shared volume. Same uses as root 1. |
| `/public/home/quanmx/` | Work root 3. Same uses as root 1. |
| `/public_bme/home/maxquan/Datasets/` | Large datasets only. Reuse datasets from this central location rather than duplicating them per project. |
| `/public_bme/home/maxquan/Datasets/models/` | Shared pretrained weights (`LAB_MODELS_DIR`): `huggingface/` is `HF_HOME`, `torch/` is `TORCH_HOME`, other weights one folder each. |
| `/tmp` | Login-node scratch only; compute nodes cannot see it. |

The three work roots are separate filesystems whose free space and quota change. Pick one by checking `df -h <root>`, `quota -s` and a probe file at the time of use (see SKILL.md); keep an existing project where it is. Datasets and weights stay in the shared `Datasets/` locations whichever root a project uses.

## Modules and environments

```bash
module ava
module load <module>
module list
module unload <module>
```

Install/configure Conda or Python environments on a login node.

## Slurm commands

```bash
sbatch <script>.sh
sinfo
pestat
squeue
scontrol show job <job-id>
scancel <job-id>
sinfo -O Nodehost,Gres:.30,GresUsed:.45
estatus | grep bme
```

## Queues and limits

| Queue | Allowed `--gres` GPU type | Hardware / pricing | Concurrent GPU limit |
| --- | --- | --- |
| `bme_gpu` | `NVIDIAA10080GBPCIe`, `NVIDIAA100-PCIE-40GB`, `TeslaV100-SXM2-32GB`, `TeslaV100S-PCIE-32GB` | Paid | 2 |
| `bme_a10080g` | `NVIDIAA10080GBPCIe` | Free; A100 PCIe 80 GB | 1 |
| `bme_gpupub` | `TeslaV100-SXM2-32GB` | Free; V100 SXM2 32 GB | 1 |
| `bme_cpu` | N/A | Paid CPU queue; do not request `--gres` | N/A |

The tutorial’s permissions list also mentions `bme_unlimited`, but gives no hardware or scheduling details. Do not choose it without current confirmation.

Use `#SBATCH -n 8`; the tutorial advises against changing it because I/O can slow down. The usual job duration is `96:00:00`; the documented maximum is `120:00:00`.

## Per-user allocation and scheduling policy

- Count `PENDING` and `RUNNING` jobs in `bme_gpu`, `bme_a10080g`, `bme_gpupub`, and `bme_cpu`. A user may have at most two such jobs in total.
- GPU requests across `bme_gpu`, `bme_a10080g`, and `bme_gpupub` may total at most three GPUs. A `bme_cpu` job uses a job slot but no GPU allocation.
- The user's requests within each GPU partition are limited to: two GPUs in `bme_gpu`, one A100 80 GB GPU in `bme_a10080g`, and one V100 GPU in `bme_gpupub`.
- Prefer the compatible resource expected to start soonest, based on `squeue`, `pestat`, `sinfo`, and `squeue --start` when available. Free queues are not preferred over paid queues. For example, if `bme_gpupub` is unavailable or expected to wait, submit a compatible V100 job to `bme_gpu`.
- Check GPU availability at the exact GRES-type level with `pestat` or `sinfo -O Nodehost,Gres:.30,GresUsed:.45`; do not treat all V100 cards as interchangeable without checking. If the workload accepts either interconnect, compare `TeslaV100S-PCIE-32GB` and `TeslaV100-SXM2-32GB` and request whichever has usable capacity expected soonest. Keep a PCIe/SXM2 constraint only when the user or workload requires it.
- Respect exact GPU type, GPU memory, and GPU-count requirements. Only choose another GPU type or `bme_cpu` when the user explicitly states that the workload is compatible.

## Distributed PyTorch example

For two GPUs, request the GPU type and count together, then match it in `torchrun`:

```bash
#SBATCH -p bme_gpu
#SBATCH -n 8
#SBATCH --mem=128G
#SBATCH --gres=gpu:NVIDIAA100-PCIE-40GB:2
#SBATCH -t 120:00:00
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err

source ~/.bashrc
source /path/to/.venv/bin/activate
cd /path/to/project
torchrun --standalone --nproc_per_node=2 -m package.train --config configs/train.yaml
```

Set `--nproc_per_node` equal to the requested GPU count. Do not put a trailing `\` on the final `torchrun` argument before a disabled/commented `--resume` line.
