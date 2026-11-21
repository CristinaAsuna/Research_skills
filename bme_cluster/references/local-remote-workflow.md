# 本地 Codex 编排，BME 集群执行

适用于用户在 Mac 提出想法、开发代码，而环境、权重、数据及实际实验放在 BME 集群的场景。沿用 `SKILL.md` 的节点、存储、队列、GPU 与作业数量约束。

## 分工和生命周期

```text
本地 Codex：设计 → 编码 → 本地轻量检查 → 分析日志/指标 → 修改下一轮实验
    │ SSH 短命令 / rsync 小文件
    ▼
登录节点：环境准备、联网下载、sbatch、查询作业
    │ Slurm 调度
    ▼
计算节点：离线训练/推理/数据预处理 → 日志、指标、checkpoint
    │ 按需回传小结果
    └───────────────────────────────→ 本地 Codex
```

批作业提交成功后由 Slurm 管理，不依赖本地 SSH 会话存活。SSH 断开、本地睡眠或聊天停止不会主动取消已经提交的批作业，但会停止本地控制与分析；不可宣称此时 Codex 仍会自动迭代。新的轮询/分析需要恢复聊天或用户另行授权的自动化。集群故障、抢占、超时仍可能终止作业，训练应保存可恢复 checkpoint。

服务器上的 Codex 可以用于独立短任务；本工作流不要求启动它，也不要求同步两边的聊天历史。

## 先确认当前条件

在本地运行短命令，禁用交互式 TTY，避免热键终端或交互式 zsh 配置干扰：

```bash
ssh -T -o BatchMode=yes -o ConnectTimeout=10 bme_login1 \
  'hostname; id -un; command -v sbatch; command -v rsync; df -h /public_bme/home/maxquan; squeue -u "$USER"'
```

`BatchMode=yes` 要求已有非交互认证。若失败，先由用户完成 SSH/密钥解锁或集群要求的认证；不要保存密码、关闭主机密钥检查或把认证凭据写入项目。命令被本地沙箱拒绝时，使用当前产品正常的审批机制，不要建议关闭全局沙箱。

按需查询 `scontrol show partition -o`、`sinfo`、`pestat`、`squeue` 和 `quota -s`。`quota` 缺失、报错或没有输出并不代表无限配额；必要时核实集群配额查询方式。

2026-10-20 本次只读实测（以后需刷新）：

- `bme_login1` 实际为 `quanmx@10.15.49.6:22112`，SSH、`sbatch`、`squeue`、`sacct`、`rsync`、`python3` 可用。
- `bme_gpu`、`bme_a10080g`、`bme_gpupub` 的分区 `MaxTime=5-00:00:00`；`bme_cpu` 为 `10-00:00:00`。本 skill 仍沿用原约定的 120 小时上限，不能仅凭分区值扩大实际申请；QOS/账户/管理员规定可能更严格。
- `df -h` 显示的是整个文件系统的余量，不是个人配额，也不保证能成功写入。大数据下载前必须现场检查（见 lab-machines 规则 8），空间不够时先解决存储位置。
- 用户报告登录节点进程超过一小时会被终止；本次未读取管理员执行策略，也未做超时实验。不能据此认定所有 Slurm 作业都只有一小时。

## 项目、数据和运行目录

默认组织方式（项目名由具体任务确定）：

```text
本地项目/                         # 可审阅的源代码、配置、小规模测试
  .cluster/runs/<run-id>.json      # 作业记录，不含密码或 token
  results/<run-id>/                # 回传的小结果

/public_bme/home/maxquan/<project>/
  envs/                           # 远端 Linux 环境，安装时明确指定 prefix
  weights/                        # 共享权重与缓存，避免重复下载
  runs/<run-id>/
    code/                         # 该次实验专用代码与配置快照
    jobs/                         # sbatch 脚本
    logs/
    outputs/                      # 含指标及 checkpoint
    submission.txt                # sbatch 原始响应

/public_bme/home/maxquan/Datasets/<dataset>/
```

不要同步 Mac 的 `.venv`、Conda 环境、`.git`、数据集、权重、checkpoint、密钥或 `.env`。在远端创建兼容 Linux/CUDA 的环境，并保留环境锁定信息。将 `HF_HOME`、`TORCH_HOME`、`XDG_CACHE_HOME`、`TMPDIR` 等实际使用的缓存/临时目录显式置于允许的存储下，提前创建目录；大数据缓存也应在 `Datasets` 下。

## 同步代码，保留每次实验版本

每轮用新的 `<run-id>`；只使用字母、数字、连字符、下划线构造项目名和运行 ID。远端目录必须在 `/public_bme/home/maxquan/` 下。数据路径采用集群绝对路径，不把本地路径直接写进 Linux 配置。

优先 rsync 明确的代码/配置目录或经过审阅的文件清单。先运行 `rsync --dry-run` 检查包含范围；普通源代码可走登录节点，大文件按原 skill 使用传输节点 `10.15.49.36:22112`，先确认该节点的认证及共享挂载，不猜测 SSH 别名。不要默认使用 `--delete`，也不要覆盖正在运行作业的代码快照。

记录 Git commit、未提交差异或同步文件清单及摘要，确保能知道实际执行了哪一版代码。依赖、权重版本和数据版本也写入本次运行记录。

## 下载与环境准备：允许中断，能够恢复

下载发生在有网络的登录节点；计算节点只读取已准备好的本地文件。数据预处理、解压等重计算应另交 CPU/GPU 作业，不能混在登录节点下载脚本里。

每个联网准备步骤应有少于一小时的明确边界，例如服务器有 GNU `timeout` 时：

```bash
# 远端 download.sh 是已检查的具体下载脚本；命令示例，不会自动执行。
ssh -T bme_login1 \
  'timeout --signal=TERM --kill-after=30s 45m bash /public_bme/home/maxquan/PROJECT/download.sh'
```

先探测 `command -v timeout`。不存在时用下载器自身的时间限制或拆成短步骤，不依赖本地 SSH 超时去杀远端进程。45 分钟是本地工作流的保守分段值，不是集群官方政策。

- 固定资源版本，优先按 shard 下载，使用支持续传的下载器；若使用 curl，确认服务端支持 Range，再用 `--continue-at -`，并配合 `--fail --location --max-time`。下载器失败和超时必须返回真实状态。
- 部分文件保留为 `.part` 或下载器自己的临时状态，成功且完成预期校验后才标记 ready。训练提交前检查完整性；不能把“目录存在”当作下载成功。
- 超时后先判断原因和空间，再在后续短步骤中续传。禁止无上限重试；同一错误连续出现三次时停下并报告原因。网络禁止、配额不足、资源不可访问时不能用重启规避。
- `pip`/Conda 安装也采用可重入短步骤；网络受限时可预备 wheelhouse。不要在包管理器仍运行时并发操作同一环境，失败安装的环境需要验证后再用于实验。
- 不在 SSH 参数或输出中暴露下载 token；使用既有安全认证方式。

超过一小时仍无法合理拆分的联网步骤，需要集群允许的下载服务/传输节点长任务策略，由管理员政策决定。不要把需要联网的下载移入无网络计算节点，也不要用 `nohup` 绕过限制。

## 提交：短 SSH 调用，持久作业记录

在用户要求执行实验的范围内完成：

1. 读取全部相关分区的当前排队/运行作业及 GPU 请求，执行原 skill 的总数与分区限制；查看实际资源，选择兼容队列。不要仅凭本地旧记录判断配额。
2. 确认环境、数据、权重和存储容量。创建独立代码快照和作业脚本，所有日志/结果路径使用绝对路径，提交前创建目录。
3. 脚本使用 `set -eo pipefail`，兼容环境初始化后可再启用 `set -u`；训练作为最后一个主命令时用 `exec python -u ...`，或显式保留训练退出码。增强版模板和生成器已启用错误传播，结尾 `echo` 不应掩盖训练失败；自定义复合命令也要检查退出码。需要加载的 module/Conda 必须显式配置，不能假设非交互 SSH 自动获得交互环境。
4. 作业中设置适合具体库的离线选项，例如 Hugging Face 的 `HF_HUB_OFFLINE=1` 与 `HF_DATASETS_OFFLINE=1`；这不替代提前下载所需文件。先做小样本/少量 step 的 GPU 验证，再按用户授权范围扩大实验。
5. 在远端切换到本次运行的明确工作目录，用 `sbatch --parsable` 提交，不使用 `--wait`。将原始响应保存为该运行的 `submission.txt`，同时回传本地；分离 `job-id;cluster` 格式中的集群后缀。
6. 本地保存 `run-id`、远端项目/代码/脚本/日志/结果路径、job ID、partition/GRES、环境路径、数据/权重版本、提交时间及代码版本。用户再次询问时按记录恢复。

提交命令示意，实际名称和脚本须根据当前实验生成：

```bash
ssh -T bme_login1 'bash -s' <<'REMOTE'
set -euo pipefail
cd /public_bme/home/maxquan/PROJECT/runs/RUN_ID
mkdir -p logs outputs
# 在进入此步骤前已检查配额；该次运行不得并行重复提交。
test ! -e submission.txt
sbatch --parsable --job-name=RUN_ID jobs/train.sbatch > submission.txt
cat submission.txt
REMOTE
```

若 SSH 在提交期间断开，`sbatch` 可能已经成功。不得立刻重试：检查远端 `submission.txt`、精确 job name、`squeue` 与 `sacct`。空记录文件、缺少 accounting 或查不到 job 都不能单独证明未提交；无法确认时报告提交状态未知，先解决不确定性。并行本地会话需要单独的互斥/预留机制，不能依赖示例中的文件检查避免竞态。

## 查询、诊断与回传

每次查询使用新 SSH 短连接，按需执行：

```bash
ssh -T bme_login1 'squeue -u "$USER"'
# 用运行记录中的真实 job ID 替换 JOB_ID。
ssh -T bme_login1 'sacct -j JOB_ID --format=JobID,JobName%40,State,ExitCode,Elapsed,MaxRSS'
ssh -T bme_login1 'tail -n 100 /absolute/path/to/run/logs/train.out'
```

不能仅凭 `squeue` 中消失判定成功；结合 `sacct` 状态/退出码、日志、预期指标与输出文件。OOM、超时、依赖缺失分别处理，不直接增加 GPU 规格或取消其他作业。

用 rsync 按清单回传指标 JSON/CSV、图片、少量日志和实验配置。权重、checkpoint、大数据继续保留在集群，只有用户需要时回传指定文件。共享运行目录可与服务器 Codex 协作，但同一时刻由一方修改某份代码；每次实验仍使用固定快照。

作业若可能超过申请时长，提前设计 checkpoint 与恢复入口。自动重排队、追加实验和取消任务必须在当前请求授权范围及资源上限内；不得把失败后的无限重试当作实验流程。

## 实际验证边界与参考

本次只验证 SSH 和只读集群查询，没有提交训练/测试作业，没有下载数据，没有验证断线恢复或一小时终止机制。使用前还需为具体项目确定环境、数据来源、GPU 需求和成功指标。

- Slurm `sbatch`：https://slurm.schedmd.com/sbatch.html （提交后返回 job ID，作业由调度器接管）
- Slurm `sacct`：https://slurm.schedmd.com/sacct.html （查询历史状态和退出码）
- OpenAI Skills：https://developers.openai.com/plugins/concepts/skills （将流程打包为指令、参考资料和必要脚本）
