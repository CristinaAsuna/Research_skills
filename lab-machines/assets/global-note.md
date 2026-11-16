<!-- lab-machines:begin -->
## 本机身份与三机协作

- 本机是 **{{MACHINE}}**（Mac 是指挥台，PC 的 WSL 是数据中心和单卡工作站，BME 集群负责大算力）。分工、路径和资产位置见 `{{REPO}}` 中的 MACHINES.md，细节见 skill `lab-machines`。
- **先看当前在哪个仓库**：
  - 在 `{{REPO}}`（读论文的 topic 工作区）里：开始前先 `git pull`，再运行 `{{PYTHON}} tools/lab.py status`；正式运行用 `tools/lab.py run start|end` 登记，零散操作用 `tools/lab.py log` 记录；结束前提交并 `git push`。
  - 在其他研究项目里：只按该仓库自己的 AGENTS.md 工作，不要去 `{{REPO}}` 做初始化，也不用 `lab.py`。
- **执行前告知**（所有仓库都适用）：任何自动执行之前（运行、下载、安装、同步、删除），先告诉用户“机器 / 目录 / 命令 / 预计耗时与显存 / 读写哪些数据”，等用户确认后再执行。
- 新下载或搬运的数据和权重登记到 `{{REPO}}` 的 MACHINES.md 资产表；Mac 上不下载数据或权重，也不放缓存。
- 想知道各机器上做过什么，在 `{{REPO}}` 里用 `tools/lab.py journal`。
<!-- lab-machines:end -->
