<!-- lab-machines:begin -->
## 本机身份与三机协作

- 本机是 **{{MACHINE}}**（Mac 是指挥台，PC 的 WSL 是数据中心和单卡工作站，BME 集群负责大算力）。分工、路径和数据资产表见总台 `{{REPO}}` 的 MACHINES.md，细节见 skill `lab-machines`。
- **执行前告知**（所有仓库都适用）：任何自动执行之前（运行、下载、安装、同步、删除），先告诉用户“机器 / 目录 / 命令 / 预计耗时与显存 / 读写哪些数据”，等用户确认后再执行。
- **多机共享记录**：每个 git 项目仓库就是自己的共享记录，在项目里用 `lab` 命令（任何目录可用）：
  - 开始：`lab status`（先自动 pull，显示正在进行的运行和最近记录）；
  - 正式运行：`lab run start <实验编号> -- <命令>`，结束后 `lab run end <run-id> --status done|failed --outputs <位置>`；
  - 零散操作（下载、装环境、清理）：`lab log "<做了什么、产物在哪>"`，不在任何仓库时记到总台；
  - 结束前提交代码，再 `lab sync`；想知道各机器做过什么：`lab journal --days N`。
- 项目目录结构、实验卡片和 STATE.md 按 skill `research-project`；各项目自己的 AGENTS.md 优先。
- 新下载或搬运的数据和权重登记到总台 `{{REPO}}` 的 MACHINES.md 资产表；Mac 上不下载数据或权重，也不放缓存。
<!-- lab-machines:end -->
