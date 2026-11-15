
<!-- lab-machines:begin -->
## 本机身份与三机协作

- 本机是 **{{MACHINE}}**（Mac 是指挥台，PC 的 WSL 是数据中心和单卡工作站，BME 集群负责大算力）。分工、路径和资产位置见研究仓库中的 MACHINES.md，细节见 skill `lab-machines`。
- 研究工作在 `{{REPO}}` 中进行：
  - 开始前先 `git pull`，再运行 `{{PYTHON}} tools/lab.py status`；
  - 结束前提交并 `git push`。
- **执行前告知**：任何自动执行之前（运行、下载、安装、同步、删除），先告诉用户“机器 / 目录 / 命令 / 预计耗时与显存 / 读写哪些数据”，等用户确认后再执行。
- **留痕**：
  - 正式运行用 `tools/lab.py run start|end` 登记；
  - 不属于 topic 的操作，做完用 `tools/lab.py log "<做了什么、产物在哪>"` 记录；
  - 想知道各机器上做过什么，用 `tools/lab.py journal`。
- 新下载或搬运的数据和权重登记到 MACHINES.md 的资产表；Mac 上不下载数据或权重，也不放缓存。
<!-- lab-machines:end -->
