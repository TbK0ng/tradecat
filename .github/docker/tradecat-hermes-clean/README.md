# tradecat-hermes-clean

这是给 WSL2 内 Docker 使用的干净 Ubuntu 服务容器。它把 Hermes 与 TradeCat
运行态放进独立 Docker volume，不挂载宿主 `~/.hermes`，避免旧会话、旧技能、
旧 gateway 状态和本机杂数据干扰 Agent 交易 loop。

## 结构

```text
WSL2 Ubuntu host Docker daemon
`-- tradecat-hermes-clean container
    |-- /opt/tradecat-public-seed         # 镜像内完整仓库种子
    |-- /workspace/tradecat-public        # 独立 project volume，首次启动从 seed 复制
    |-- /home/ubuntu/.hermes              # 独立 Hermes home volume
    |-- /home/ubuntu/.codex               # 独立 Codex home volume
    |-- /opt/tradecat-venv                # 独立 TradeCat editable venv volume
    `-- /home/ubuntu/.tradecat-runtime    # 独立 paper/watch runtime volume
```

## 使用

```bash
cp .github/docker/tradecat-hermes-clean/container.env.example docker/tradecat-hermes-clean/container.env
bash .github/scripts/tradecat-hermes-container.sh build
bash .github/scripts/tradecat-hermes-container.sh up
bash .github/scripts/tradecat-hermes-container.sh shell
```

## HexHub / SSH 进入

启动容器：

```bash
bash .github/scripts/tradecat-hermes-container.sh build
bash .github/scripts/tradecat-hermes-container.sh up
```

HexHub 里填写：

```text
名称: tradecat-hermes-clean
Host: 127.0.0.1
User: ubuntu
端口: 2222
认证: 密码
密码: ubuntu
```

SSH 只绑定本机 `127.0.0.1:2222`，不暴露到局域网或公网；容器内禁用 root 登录和公钥登录。

容器默认只保持空闲常驻，不自动启动 Hermes gateway，也不自动启动 paper loop。
进入容器后可以手动执行：

```bash
hermes version
codex --version
python3 -m json.tool .github/skills/tradecat-public/agents/manifest.json >/dev/null
bash .github/scripts/agent-smoke.sh
bash .github/scripts/start-auto-paper.sh status --json
```

镜像默认安装构建时 Hermes 上游 `main` 与 Codex CLI `0.133.0`。需要完全可复现时，
在 `docker/tradecat-hermes-clean/container.env` 里把 `HERMES_REF` 覆盖成固定 commit。
如果只想清空
Hermes/Codex 的 home 运行态，不重置项目代码、venv 或 paper/watch runtime，运行：

```bash
bash .github/scripts/tradecat-hermes-container.sh reset-agent-homes
```

`/workspace/tradecat-public` 不是宿主 bind mount。它是容器自己的 Docker volume，
第一次启动时从 `/opt/tradecat-public-seed` 复制完整仓库。你可以在容器内直接调试、
改文件和跑测试；这些改动保留在 `tradecat_project` volume 中。只有修改 Dockerfile、
系统依赖或想刷新镜像种子时才需要 rebuild。需要用镜像种子重置项目 volume 时运行：

```bash
bash .github/scripts/tradecat-hermes-container.sh refresh-project
```

## Telegram

把 token 写进 ignored `docker/tradecat-hermes-clean/container.env`，不要写入 Git：

```bash
printf 'HERMES_TELEGRAM_BOT_TOKEN=%s\n' '<token>' >> docker/tradecat-hermes-clean/container.env
```

具体 Hermes gateway 命令以本机 Hermes 版本为准；容器保证提供隔离的
`HERMES_HOME=/home/ubuntu/.hermes`、`CODEX_HOME=/home/ubuntu/.codex`、
已安装的 `codex` CLI，以及已挂载到 Hermes/Codex homes 的 `tradecat-public` skill。
