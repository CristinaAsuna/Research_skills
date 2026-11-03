# Research Skills

Personal, reusable skills for research and computing workflows. Each top-level
directory is one self-contained skill and can carry its own instructions,
references, templates, and helper scripts.

## Available skills

| Directory | Skill | Purpose |
| --- | --- | --- |
| [`bme_cluster`](bme_cluster/) | `bme-cluster` | Prepare, submit, monitor, and debug Slurm CPU/GPU jobs on the BME cluster while enforcing its node, network, storage, and resource-allocation constraints. |
| [`paper-algorithm-tutorial`](paper-algorithm-tutorial/) | `paper-algorithm-tutorial` | Turn a research paper into a Chinese hands-on implementation course with microtasks, layered hints, reference solutions, a runnable practice model and mechanism checks. Includes an adapter for the tutorial repository. |
| [`research-discovery-lab`](research-discovery-lab/) | `research-discovery-lab` | Reconstruct how a paper's idea was discovered, have the user predict first, then replay it with toy experiments and figures in a workspace with planner/executor/reviewer roles, frozen predictions, a growth log and approval-gated harness self-improvement (RSI). |

## Use a skill locally

Copy a skill directory into the local skill directory, preserving its contents.
For example:

```bash
cp -a bme_cluster ~/.agents/skills/bme-cluster
```

Then invoke it as `$bme-cluster` where supported. Read the skill's `SKILL.md`
before using its templates or helper scripts.

For paper tutorials, invoke `$paper-algorithm-tutorial I-JEPA`. In the existing
tutorial workspace, a paper name alone also uses its project instructions.
Keep this repository's skill directory as the maintained source and copy the
complete folder to `~/.agents/skills/paper-algorithm-tutorial` after updates;
verify the copies match. The installed folder is a separate file copy, not a symlink.

## Repository layout

```text
<skill-directory>/
├── SKILL.md        # Required skill instructions and metadata
├── agents/         # Optional UI metadata
├── assets/         # Templates copied into generated work
├── references/     # Task-specific documentation
└── scripts/        # Reusable helper scripts
```

## Add a skill

1. Create a lowercase skill directory at the repository root; prefer hyphens unless an existing naming convention requires underscores.
2. Add a `SKILL.md` with YAML frontmatter containing its `name` and a concise,
   discriminating `description`.
3. Add only the assets, references, and scripts that directly support the
   skill; keep conditional detail in `references/`.
4. Validate the skill before committing:

   ```bash
   python3 /path/to/skill-creator/scripts/quick_validate.py <skill-directory>
   ```

See [`bme_cluster`](bme_cluster/) for a complete example.
