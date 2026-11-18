# 在 PC（WSL）上工作

## 连接

- **agent 和 rsync**：用 `ssh pc '<命令>'`。它直接连到 WSL 内的 sshd（2222 端口），拿到的是完整的 Linux shell。
- **人手动使用**：可以继续用 `windows-linux`。这个别名会强制打开交互终端，所以不能用于 rsync，也不能执行单条命令。
- **`ssh pc` 超时**：通常是 WSL 没在运行，例如 Windows 刚重启过（sshd 跟着 WSL 一起启动）。先用 `ssh windows "wsl.exe -d Ubuntu-24.04 -u pc --exec true"` 唤醒，几秒后重试。`.wslconfig` 中已设置 `[wsl2] vmIdleTimeout=-1` 和 `[general] instanceIdleTimeout=-1`，WSL 空闲时不会自动关闭。修改 `.wslconfig` 后要执行一次 `wsl --shutdown` 才会生效。
- **只需要 Windows 侧信息时**（显卡驱动、磁盘、`wsl.exe`）：用 `ssh windows`，默认 shell 是 PowerShell 5.1，不支持用 `&&` 连接命令。

## 运行前检查

1. 先看显存：

   ```bash
   nvidia-smi --query-gpu=memory.used,memory.total --format=csv
   ```

   Zotero 翻译模型常驻约 6 GB。剩余显存不够时，告诉用户并建议改到集群运行，不要擅自停掉翻译服务。
2. 用 `~/lab/envs/main/bin/python`。不要用 Windows 侧的 Python 3.14，也不要在全局安装 torch。
3. 这台机器已有的规则要求缓存路径只对相关命令设置，所以不要把它们写进全局 shell 配置，每次运行时显式带上：

   ```bash
   HF_ENDPOINT=https://hf-mirror.com
   HF_HOME=/mnt/d/vscode_workplace/brainstorm/models/huggingface
   UV_CACHE_DIR=~/lab/assets/cache/uv
   ```

## 长时间运行

- 用 tmux 启动，并把会话名作为 `--job` 传给 `lab run start`：

  ```bash
  tmux new -d -s <run-id> 'cd <运行目录> && <命令> 2>&1 | tee run.log'
  ```

  不要用 `nohup` 挂在 SSH 会话上。
- `.wslconfig` 中设置了 `vmIdleTimeout=-1`，WSL 空闲时不会关闭。但 Windows 重启或系统更新仍会中断运行，所以长训练要能保存 checkpoint 并从中恢复。
- 查看运行状态：

  ```bash
  ssh pc 'tmux ls; tail -n 50 <运行目录>/run.log'
  ```

## 数据放哪里

| 数据类型 | 位置 | 原因 |
|---|---|---|
| 大量小文件的数据集、预处理缓存、训练产物 | ext4：`~/lab/assets`、项目的 `runs/` | 读写快 |
| 权重 | D: 盘上已有的库 `/mnt/d/vscode_workplace/brainstorm/models` | 文件大、数量少，走 9p 也能接受 |
| 完成后不再频繁访问的大产物 | `/mnt/d/lab-archive` | 冷归档 |

- 新数据集和权重都要登记到 `MACHINES.md` 的资产表。
- 不要从 `/mnt/d` 直接读取大量小文件做训练，先复制到 ext4。
- 归档到 D: 盘之后，在运行记录的 `outputs` 字段里更新位置。
