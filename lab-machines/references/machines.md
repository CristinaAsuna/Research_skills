# 三台机器的具体配置

2026-11-14 只读调查所得，主机、空间和 GPU 占用会变化，使用前重新确认。

## Mac（`mac`）

- 本机 926 GiB，不放数据、权重和缓存。
- 总台仓库（资产表和零散操作日志）：`/Users/max/codebase/coding_agent_repro`；项目仓库在 `/Users/max/codebase/<项目>`。
- skill 源码：`/Users/max/codebase/research_plugins/Research_skills`
  - `~/.claude/skills/` 下软链接到这里，供 Claude Code 使用；
  - `~/.agents/skills/` 下软链接到这里，供 Codex 使用。
- Python：`/Users/max/codebase/.ml/.venv/bin/python`（3.11，含 torch，MPS 可用）。
- rsync：需要用 Homebrew 安装 3.x 版本，即 `/opt/homebrew/bin/rsync`。苹果自带的 openrsync 版本太旧。
- 联网走本地代理 127.0.0.1:7897。
- SSH 别名：

  | 别名 | 地址 | 用途 |
  |---|---|---|
  | `pc` | 10.19.125.87:2222 | 直接进 WSL |
  | `windows` | 10.19.125.87:22 | Windows PowerShell |
  | `windows-linux` | — | 强制打开交互式 WSL 终端，只适合人手动使用 |
  | `bme_login1` | 10.15.49.6:22112 | 集群登录节点 |
  | `bme_login2` | 10.15.49.7:22112 | 集群登录节点 |
  | `bme_xfer` | 10.15.49.36:22112 | 集群传输节点 |

## PC（`pc`，WSL2 Ubuntu 24.04）

- **硬件**：Windows 11，内存 63.7 GB，其中 WSL 分到 40 GB 和 20 个核；GPU 为 RTX 3060 12 GB。Zotero 翻译模型常驻约 6 GB 显存，实际可用约 6 GB，运行前用 `nvidia-smi` 确认。
- **磁盘**：
  - WSL ext4 虚拟盘：约 1 TB，读写快，剩约 950 GB。
  - D: 盘：3.7 TB，剩约 2.7 TB。从 WSL 访问走 `/mnt/d`（9p），对大量小文件很慢，读大文件尚可。
- **路径**：

  | 用途 | 路径 |
  |---|---|
  | 总台仓库 | `~/lab/coding_agent_repro` |
  | 项目仓库 | `~/lab/<项目>` |
  | 运行产物 | 项目的 `runs/`（被 git 忽略）；想集中存放就设 `LAB_RUNS_ROOT=~/lab/runs` |
  | 热数据与缓存（数据集、HF 缓存） | `~/lab/assets`，放在 ext4 上 |
  | Python 环境 | `~/lab/envs/main`（uv 建的 venv，torch CUDA） |
  | 已有权重库（保留并继续使用） | `/mnt/d/vscode_workplace/brainstorm/models`，含 huggingface、torchhub、dit、sit |
  | 冷归档 | `/mnt/d/lab-archive` |

- **联网**：huggingface.co 不通，使用 `HF_ENDPOINT=https://hf-mirror.com`；GitHub 可以访问。
- **其他**：
  - WSL 的 `~/.codex/AGENTS.md` 里已有用户自己写的规则，只追加，不覆盖。
  - WSL 空闲时会关闭，需要在 `.wslconfig` 中设置 `vmIdleTimeout=-1`。

## 集群（`cluster`）

- **约束**：遵循 bme-cluster skill，包括计算节点不能联网、每人最多 2 个作业和 3 张 GPU、`/public_bme2` 只在用户明确指定路径时才写。
- **路径**：
  - 总台仓库：`/public_bme/home/maxquan/Projects/coding_agent_repro`
  - 项目仓库：`/public_bme/home/maxquan/Projects/<项目>`，运行产物在项目的 `runs/` 下（或用 `LAB_RUNS_ROOT` 指向别处）
  - 数据集：`/public_bme/home/maxquan/Datasets`
  - 权重：`/public_bme/home/maxquan/Datasets/models`，`~/.bashrc` 里设为 `LAB_MODELS_DIR`。hf 下载进 `huggingface/`（`HF_HOME`），torch.hub 进 `torch/`（`TORCH_HOME`），其他手动下载的权重各占一个子目录。不在项目目录里另存权重。
- **`lab` 用的 Python**：系统只有 3.6 和 3.7。用 uv 安装独立的 3.12，安装目录放在 `/public_bme/home/maxquan/envs/` 下，不放在 home。
- **联网**：登录节点能访问 hf-mirror.com 和 GitHub，huggingface.co 不通。
- **GPU**：A100 40G/80G 和 V100，共约 100 张，通常需要排队。
