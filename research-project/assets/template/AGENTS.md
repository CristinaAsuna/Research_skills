# {{NAME}}：项目规则

本文件只放长期有效的规则，上限 80 行。进度写在 STATE.md，不写在这里。

## 1. 新会话先做

1. `git pull`，然后依次读：本文件、STATE.md、STATE.md 指向的那一张卡片。
2. 需要细节时再读 docs/ 里对应的一份文档。不读 runs/、scratch/ 和其他实验的目录。
3. 用户的要求超出当前卡片时，先指出来，再问是否新开卡片。

## 2. 文件地图

| 内容 | 唯一的位置 |
| --- | --- |
| 当前主干、当前唯一问题、排队、搁置的想法 | STATE.md（≤40 行） |
| 全部实验的一句话结论 | EXPERIMENTS.md（每个实验一行） |
| 目标、背景、已有结论 | docs/PROJECT.md |
| 数据来源、契约、划分 | docs/DATA.md |
| 数据→训练→推理→评测的命令，唯一的评测入口 | docs/PIPELINE.md |
| 决策及理由 | docs/DECISIONS.md（每条 ≤5 行） |
| 单个实验的问题、预测、结果 | experiments/<id>/CARD.md（≤40 行） |

- 不新增其他 Markdown 文件。确实需要新的文件类型时，先问用户。
- 同一条契约或结论只在一处写全，其他地方只引用。
- 文档是合并改写的：改已有条目，不按日期往下追加，不写会话日记。超过行数上限就删减。

## 3. 实验准入

- 没有用户批准的卡片，不写实验代码，也不运行实验。新建卡片用 `tools/project.py new <slug> --type <类型>`。
- 做当前卡片时想到的其他实验，写进 STATE.md 的"搁置的想法"，不执行。
- 卡片必须写明：两种结果分别导致下一步做什么。两种结果走向相同，就不做这个实验。
- 预测和推翻条件在运行前写好，运行后不改。不为了得到预测的结果去调参、挑 seed 或换指标。
- 四种类型：
  - **trunk**：让端到端流程出一个可信的数，同一时间只有一个。
  - **ablation**：主干加一处改动。
  - **analysis**：解释主干的行为，读主干已缓存的推理结果，不重新生成。
  - **spike**：试一个新方向。在 scratch/ 里做，卡片写明时间上限和停止门槛；到期后要么转成一张新卡片，要么只在 EXPERIMENTS.md 留一行结论。

## 4. 代码放在哪里

- 主干代码在 `src/{{PKG}}/`。实验写成 `configs/exp/<id>.yaml`（只列相对 `configs/trunk.yaml` 的差异），必要时在 src 里加一个默认关闭的开关。不为一个实验新建包。
- `experiments/<id>/` 里的脚本可以 import src；src 和其他实验都不能 import 它。
- 评测只用 docs/PIPELINE.md 写的那一个入口和那一个评测集。不另写评测脚本。更换评测集或主指标属于决策，要记进 docs/DECISIONS.md。

## 5. 产物

- 进 git 的只有：代码、配置、文档、`experiments/<id>/` 下的 CARD.md、result.json 和不超过 4 张 PNG。
- `result.json` 至少包含：exp、commit、config、eval_set、metrics、baseline、runtime_sec、outputs（大产物所在的机器和路径）。
- 大产物放在 `runs/<id>/`，不进 git：
  - checkpoint 只留 best；训练进行中多留一个 last。
  - 推理结果和特征缓存，同一组"checkpoint、数据划分、配置"只存一份，新实验直接读它。
  - 每类结果只存一种格式：指标 JSON，图 PNG。逐样本数组、HTML 报告等只在卡片列出时才导出。
- 卡片没列的临时文件写到 scratch/。虚拟环境和工具缓存（matplotlib、CUDA、HF）不放进 runs/ 和 experiments/。
- 不删除、移动或覆盖已有的数据、权重和 runs/；需要清理时列出清单让用户决定。

## 6. Git

- 正式运行前 `src/`、`configs/`、`tests/` 必须已提交，把 commit 写进 result.json。
- 每次会话结束：更新 STATE.md 和 EXPERIMENTS.md 里对应的一行，运行 `tools/project.py check`，提交并 push。
- 提交信息写清做了什么，例如 `exp(<id>): …`、`trunk: …`、`docs: …`。

## 7. 主干迁移

只有两种情况可以改 `configs/trunk.yaml` 和 STATE.md 的主干一节：

- **实验取代主干**：卡片里事先写好的条件（同一评测集、超过主干多少、几个 seed）已经满足，并且用户同意。然后合并配置，打 tag `trunk-v<N>`，更新 STATE.md，在 docs/DECISIONS.md 记一条。旧主干在 EXPERIMENTS.md 里保留为基线行。
- **从旧项目搬入**：按 skill `research-project` 的 references/trunk-migration.md 逐步做。

## 8. 执行和分工

- 运行、下载、安装、同步、删除之前，先告诉用户"机器 / 目录 / 命令 / 预计耗时与显存 / 读写哪些数据"，等确认后再执行。在哪台机器上跑，按 skill `lab-machines` 和 `bme-cluster`。
- subagent 只用于读得多、返回少的工作：翻日志、汇总指标、查代码、读论文、核对数字，返回结论和文件路径。实验设计、是否偏离主干的判断、文档修改留在主会话。
- 一个实验做完后，由用户或新会话核对 result.json 与卡片结论是否一致，再把状态改为 done。
