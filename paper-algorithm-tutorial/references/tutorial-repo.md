# tutorial 仓库适配

仅用于 `/Users/max/codebase/scratch/tutorial` 或用户明确指定的同一项目 checkout。先读取实际目录、AGENTS.md 和 README；此文件是适配说明，不是未来文件状态的证明。

## 入口与学习约定

根 AGENTS.md 将仅输入论文名称解释为课程创建/完善；明确解读、比较、排错请求仍优先。读取根 README、目标目录 README、docs/project_memory.md 和相近课程。根据任务读取课程质量约定与 docs/paper_workflow.md。

现有默认：中文细步骤、手算例子、微任务 TODO、三级提示、参考解、学生 practice、局部检查、CPU demo、recipe。新增课程保留这个合同，先检查已有课程和学生填答。MAE 中存在填答，不能因为还有 TODO 注释而重置。

## 组件归属

|位置|职责|
|---|---|
|mllm/|视觉自监督、多模态、ACT 动作策略课程|
|generative_model/|生成模型算法和训练|
|general_utils/edu_core|token attention、像素切片/embedding、位置编码、mask、padding、freeze/EMA 和状态工具|
|general_utils/utils|已有生成模型工具，不把扩散空间 attention 约定混入 token 课程|
|mllm/foundations/|基础练一次；后续论文复用共享参考组件|

检查实际 API 再使用。无损 patchify 与可学习 PatchEmbed 不同；2D 共享局部像素顺序 `(p,p,C)`，3D 为 `(t,p,p,C)`，网格宽度变化最快。Conv 权重展平需对齐这一顺序。

edu_core attention mask 的 True 表示允许看见。EMA helper 只更新 parameters；teacher frozen/eval、center buffers、更新顺序由课程明确管理。纯 encoder 可用 SelfAttentionBlock；不为统一接口强改已有 checkpoint 参数布局。

## 当前教程版本

DINO+iBOT 机制 toy、原始 I-JEPA/V-JEPA、LLaVA-1.5、Flamingo、InstructBLIP 和 ACT 核心机制。用户明确要求后续版本时新增或区分版本，不替换已有学习内容。

## 验证与维护入口

从仓库根提供命令，用依赖已确认的 Python。例如：

```bash
PYTHONPATH=general_utils/edu_core python3 mllm/<paper>/check_lessons.py --lesson 1
PYTHONPATH=general_utils/edu_core python3 mllm/<paper>/run_<paper>_demo.py --implementation reference
PYTHONPATH=general_utils/edu_core python3 mllm/<paper>/run_<paper>_demo.py --implementation practice
```

共享包可安装到用户选择的环境。不要硬编码本机解释器；历史验证的 `.ml` 环境必须重新确认才能使用。

新增 MLLM 课程同步更新 mllm/README.md、mllm/check_tutorials.py 的 DEMOS/WIRING 注册。其他领域更新对应索引和运行入口，不强行注册到 MLLM runner。

长期文档索引在 docs/project_memory.md；设计写到 teaching_design.md，运行结果写到 validation.md，学习进度不自动推断。记录日期、环境、实际命令、范围；未重跑的旧结果保留原日期。个人 Codex 记忆不是同步目标。
