# 机器之间搬数据

原则：

- 大文件不经过 Mac。
- 谁用谁下载。
- 先复制、再核对、最后由用户决定是否删除原件。
- 每次搬运都先 `--dry-run`，并按“执行前告知”向用户说明来源、目标、大小和预计耗时。

## 各条路线

| 路线 | 用途 | 方式 |
|---|---|---|
| Mac → PC | 迁移旧数据、偶尔推送小文件 | `/opt/homebrew/bin/rsync -aH --partial --info=progress2 <源>/ pc:<目标>/` |
| PC → Mac | 小结果、图 | 走 git：在 PC 上提交并 push，在 Mac 上 pull。必要时可 rsync 单个文件 |
| PC ↔ 集群 | 数据集、权重、checkpoint | 在 WSL 上直接连传输节点：`rsync -aH --partial <源>/ bme_xfer:/public_bme/home/maxquan/<目标>/`；没有 rsync 时用 `sftp bme_xfer` |
| 集群下载 | 权重、数据 | 在登录节点用 hf-mirror 下载，单次不超过 45 分钟并设置超时，规则见 bme-cluster |
| PC 下载 | 权重、数据 | 在 WSL 中设置 `HF_ENDPOINT=https://hf-mirror.com` 后下载 |

## 核对

- 有 registry 或 manifest 记录了 sha256 的，逐个文件比对。
- 没有记录的，在两边对同一组文件计算 `sha256sum` 后比对，或用 `rsync -c --dry-run` 确认没有差异。
- 核对结果写进 `lab log` 的说明，例如“迁移 X，N 个文件，sha256 全部一致，原件仍在 Mac 上”。
- 更新 `MACHINES.md` 资产表中的位置和大小。

## 注意

- 不用 `--delete`，不覆盖目标端较新的文件；合并到已有目录时先 `--dry-run` 看清会覆盖什么。
- 集群上的大文件写到三个工作根目录之一（见 machines.md 的可写目录表），数据集和权重统一放 `/public_bme/home/maxquan/Datasets/`。写之前按 SKILL.md 规则 8 检查空间；不写家目录，除非用户同意。
- 不要把 `.venv`、conda 环境、`.git` 或密钥同步到另一台机器，各机器在本机重建环境。
