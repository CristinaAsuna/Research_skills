---
name: research-discovery-lab
description: "Reconstruct how a research paper's idea was likely discovered (prior belief → surprising observation → hypothesis → experiment), then design small toy experiments and visualizations that let the user re-live that discovery, inside a growth-oriented workspace with planner/executor/reviewer roles, frozen predictions, image-rich summaries, a learner growth log and approval-gated harness self-improvement. Use when the user asks why or how a paper's motivation arose, wants to replay a paper's discovery with toy experiments, wants to open, plan, execute or review a topic or run a retro in a discovery-lab workspace (a directory with lab.toml), or wants such a workspace initialized. Not for plain paper summaries, full reproductions of paper metrics, or from-scratch implementation tutorials (use paper-algorithm-tutorial)."
---

# Research Discovery Lab

Grow a junior researcher's ability and taste by replaying how a paper's idea was discovered: what the authors saw, why it was surprising, how they reasoned, and which experiment settled it. The user's growth is the goal; experiment results are the means. Default to Chinese for discussion and documents; code and file names stay English.

## Find the workspace and obey its rules

- A workspace is the nearest directory (cwd or a parent) containing `lab.toml`. Read its `AGENTS.md` first. Workspace rules evolve through approved harness proposals and override this skill's defaults.
- Workspace tool: `<python> tools/lab.py status | new <slug> --paper "<title or arXiv>" | check [topic] [--phase P]`, with `<python>` from `lab.toml [env].python` (Python ≥3.11).
- No workspace and the user wants one: `<python> scripts/lab.py init <root>`. It only creates missing files and never overwrites. `init <root> --upgrade` prints diffs of rules, templates and tools against this skill without writing anything. Do not create a workspace for a pure discussion.

## Pick the role

| Request | Role | Read before acting |
| --- | --- | --- |
| Open a topic, replay a paper's discovery, design toys | Planner | [discovery-reconstruction](references/discovery-reconstruction.md), [toy-and-figures](references/toy-and-figures.md) |
| Execute `topics/<id>/PLAN.md` | Executor | Workspace `AGENTS.md` §4 and the topic's PLAN.md; [toy-and-figures](references/toy-and-figures.md) §3–4 for plotting |
| Review a topic, reflect with the user | Reviewer | [review-and-growth](references/review-and-growth.md) |
| Retro, harness proposal, upstreaming | Reviewer | [harness-rsi](references/harness-rsi.md) |

Prefer that the Reviewer is not the session that executed the topic.

## Planner

1. Run `lab.py status`. Read `LEARNING.md` (the user's stage decides which questions you ask and what you reveal), `EXPERIMENTS.md`, and the relevant parts of `INSIGHTS.md` and `RESEARCH_MOVES.md`.
2. Read the actual paper: the relevant sections, figures and appendix, plus official code, the authors' earlier papers or OpenReview discussion when useful. Record what you read. Never reconstruct from abstracts, search snippets or secondary summaries alone without saying so.
3. Predict first. Before revealing any reconstruction, ask 2–3 stage-appropriate questions from the question bank. In Claude Code use AskUserQuestion with free-text answers allowed. Record answers verbatim with the date. If the user skips, record that and move on.
4. Write DISCOVERY.md: prior belief, pivot observation, reasoning chain with an evidence label and confidence on every link, at least one alternative discovery path, and competing explanations.
5. Write PLAN.md as a self-contained spec, because the executor cannot see the chat. E1 relives the surprise. E2 manipulates the hypothesized factor. Optional E3+ tests a competing explanation. Default to L1 toys within the workspace compute budget, and write figure specs before any code.
6. After the user approves: create the topic with `lab.py new`, fill DISCOVERY.md and PLAN.md, set the status to `planned` in EXPERIMENTS.md, run `lab.py check topics/<id>`, and commit `plan(<id>): …`. That commit freezes the predictions. In Claude Code plan mode only the plan file is writable, so draft there and write the topic files after ExitPlanMode.

## Executor

Follow workspace `AGENTS.md` §4. In short: run a smoke test before the formal runs, stay inside the budget, never tune for the predicted outcome, write `results/E*.json` and figures, fill every SUMMARY.md section including deviations, pass `check --phase executed`, then commit `run(<id>): …`.

## Reviewer

1. Verify before reflecting. Spot-check SUMMARY numbers against `results/*.json`, open every figure, and confirm the toy claims are not stated as paper claims.
2. Run the reflection dialogue in [review-and-growth](references/review-and-growth.md). The user's taste judgments must be the user's own words.
3. Merge updates into EXPERIMENTS, INSIGHTS, RESEARCH_MOVES and LEARNING. Record friction metrics in HARNESS_LOG and write proposals only when the evidence threshold is met.
4. Pass `check --phase reviewed`, then commit `review(<id>): …`. After every 5 reviewed topics, offer a retro.

## Guardrails

- Never fabricate author quotes, motivations, talks, or the user's reflections. Label inference as `[推断]`. Quote at most 15 words from a source.
- A toy result is never a paper reproduction. State what each toy cannot show.
- Propose harness changes; never apply changes to `AGENTS.md`, `CLAUDE.md`, `lab.toml`, `templates/` or `tools/` without the user's approval.
- Keep the fixed topic files and line budgets. Merge or rewrite instead of appending, and do not create extra Markdown files.
- Respect the session's mode: plan only in plan mode, and execute only within the approved PLAN.md.
