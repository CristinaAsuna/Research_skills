#!/bin/bash
# Copy this file before editing. Submit the copy with: sbatch <job-script>.sh
# All dependencies, models, and data must already be present: compute nodes have no network.

#SBATCH -J <job-name>
#SBATCH -N 1
#SBATCH -p bme_cpu
#SBATCH -n 8
#SBATCH --mem=32G
#SBATCH -t 96:00:00
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err

echo "${SLURM_JOB_NODELIST}"
echo "start on $(date)"

# Option A: source ~/.bashrc && conda activate <conda-environment>
# Option B: source /absolute/path/to/.venv/bin/activate
python <entrypoint.py> <arguments>

echo "end on $(date)"
