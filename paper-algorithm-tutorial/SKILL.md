---
name: paper-algorithm-tutorial
description: "Create or improve hands-on, from-scratch algorithm tutorials from research papers, with Chinese step-by-step exercises, layered hints, reference solutions and a runnable practice model. Use for requests to turn a paper into an implementation course, including paper-name-only requests in a tutorial workspace. Do not reinterpret explicit paper-summary, comparison or production-training requests as course creation."
---

# 论文算法动手教程

Turn a paper into a course a learner can complete without already knowing the implementation. Default to Chinese explanations and PyTorch CPU toy experiments; preserve explicit choices of language, framework, scale and output location.

## Establish the request and workspace

- Accept a title, acronym, paper URL or local paper. A workspace is established for tutorials when its local instructions or the user's request specify that purpose, not merely because its directory is named tutorial. In that context, a paper name alone requests course creation or improvement. Elsewhere, follow the explicit request; do not take over a summary or comparison task.
- Inspect local instructions, existing courses, shared components and student edits. Use the requested project or current workspace; do not silently write to a different repository.
- Read [the teaching contract](references/teaching-contract.md) when creating or substantially improving a course. It defines the exercises, implementation interfaces and acceptance criteria.
- Only when working in `/Users/max/codebase/scratch/tutorial` or an explicitly identified checkout of that project, read [the repository adapter](references/tutorial-repo.md). Other projects do not require its paths or `edu_core` package.
- Respect the session's operating mode: plan in Plan mode; implement and validate when execution is permitted. Do not repeatedly ask for established teaching preferences.

## Identify the paper and its defining mechanism

Locate and actually read the original paper's relevant sections and official implementation, where available. Record the exact title, year/version, links and the relevant equations or source locations. Use the paper when no official code exists; say which evidence is unavailable. Do not infer architecture or losses from a search snippet or secondary summary.

Use the explicitly requested version first, then the workspace's confirmed version. Otherwise, for a recognizable unversioned name, use the original same-name paper and briefly state that choice. An acronym shared by materially different algorithms is not a unique identity; ask a focused identity question when the workspace cannot disambiguate it.

Draw the data flow and identify inputs, representations, tensor shapes, trainable modules, targets, masks, stop-gradient and update order. Distinguish the defining mechanism from infrastructure, and document every teaching simplification that changes paper behavior.

## Build the learning path

Start with prerequisites the learner can practice once. Reuse suitable shared attention, patchification, masking and training primitives; add shared code only when it is genuinely reusable. Keep paper-specific objectives and routing in the course.

For each defining mechanism, provide a purpose, shape derivation, hand-worked example, initialized module scaffold and numbered microtasks. Complex batch packing or random searches need an outer scaffold and a small deterministic exercise first. Three optional hint levels progress from reasoning to operations to pseudocode. A blank function plus “see reference” is insufficient.

Produce a complete reference solution and an intentionally incomplete practice path. The practice model must call the learner's functions, including the relevant loss and training step; provided peripheral toy backbones are allowed. Use explicit composition or replacement methods. Never fall back to a reference answer when a TODO raises.

## Validate and deliver

Confirm the Python/framework environment. Run focused mechanism checks and the reference CPU demo; validate student routing with test substitutes and verify that unfinished exercises report their specific TODO with a nonzero exit code. Static compilation, reference success and substitute-based wiring success are different evidence; none proves the learner has completed the exercises.

Update the project's course index and validation entry points when applicable. Preserve filled exercises and unrelated work. Include a real-data/weights/evaluation route without claiming paper metrics were reproduced. Report the selected paper, generated course location, actual verification and the first practice command.

If the paper or dependencies cannot be accessed, identify the missing evidence or unverified execution precisely. Do not invent paper details, completed tests or a successful reproduction.
