# Deployment and Operations

TradeCat Public 不部署真实交易服务。可运行形态只有本地 public-readonly + paper/watch。
逐步操作清单见 `.github/docs/operations-runbook.md`。

## 安装

```bash
python3 -m pip install -c constraints.txt -e ".[dev]"
```

## WSL2 内干净 Hermes 容器

当宿主 `~/.hermes` 已经包含旧会话、旧技能、gateway 状态或其他项目数据时，
不要继续复用宿主 Hermes home。推荐在 WSL2 Ubuntu 的 Docker daemon 里启动一个独立
Ubuntu 服务容器：

```text
Windows
`-- WSL2 Ubuntu host
    |-- Docker Engine
    `-- tradecat-hermes-clean container
        |-- /opt/tradecat-public-seed         # 镜像内完整仓库种子
        |-- /workspace/tradecat-public        # 独立 project volume
        |-- /home/ubuntu/.hermes              # 独立 Hermes home volume
        |-- /home/ubuntu/.codex               # 独立 Codex home volume
        |-- /opt/tradecat-venv                # 独立 TradeCat editable venv volume
        `-- /home/ubuntu/.tradecat-runtime    # 独立 paper/watch runtime volume
```

启动：

```bash
cp .github/docker/tradecat-hermes-clean/container.env.example docker/tradecat-hermes-clean/container.env
bash .github/scripts/tradecat-hermes-container.sh config
bash .github/scripts/tradecat-hermes-container.sh build
bash .github/scripts/tradecat-hermes-container.sh up
bash .github/scripts/tradecat-hermes-container.sh verify
```

进入容器：

```bash
bash .github/scripts/tradecat-hermes-container.sh shell
```

HexHub/SSH 进入：

```text
Host: 127.0.0.1
Port: 2222
User: ubuntu
Password: ubuntu
```

该 SSH 入口只绑定 `127.0.0.1:2222`，容器内禁用 root 登录和公钥登录。

容器默认 `sleep infinity`，只提供干净服务环境，不自动启动 Hermes gateway、Codex 或
paper loop。需要 Telegram 时，把 token 写入 ignored
`docker/tradecat-hermes-clean/container.env`。需要代理时，只在这个 ignored env 文件里显式写
`HTTP_PROXY=http://host.docker.internal:7890` 和
`HTTPS_PROXY=http://host.docker.internal:7890`。不要把宿主
`127.0.0.1:7890` 直接透传进容器，因为容器内 `127.0.0.1` 指向容器自身；
Compose 已配置 `host.docker.internal:host-gateway`。

镜像默认安装构建时 Hermes 上游 `main` 与 Codex CLI `0.133.0`。需要完全可复现时，
在 `docker/tradecat-hermes-clean/container.env` 里把 `HERMES_REF` 覆盖成固定 commit。
需要清空
Hermes/Codex home 运行态时，使用：

```bash
bash .github/scripts/tradecat-hermes-container.sh reset-agent-homes
```

该命令只重建 `/home/ubuntu/.hermes` 和 `/home/ubuntu/.codex` 对应 volume，不会删除
`/workspace/tradecat-public`、`/opt/tradecat-venv` 或 `/home/ubuntu/.tradecat-runtime`。

资源默认限制为 `2 CPU / 4 GiB RAM`，日志轮转为 `10 MiB * 3`。这是本地隔离运行面，
不是生产实盘部署面；安全边界仍然是 public-readonly + paper/watch。

注意：`/workspace/tradecat-public` 是容器内独立 project volume，不是宿主 bind mount。
首次启动会从镜像内 `/opt/tradecat-public-seed` 复制完整仓库。容器内调试改动会保留在
`tradecat_project` volume；只有 Dockerfile、系统依赖或镜像种子变化才需要 rebuild。

## 本地 paper/watch

默认运维口径是手动运行，不常驻。启动 loop 会持续读取公开在线表格、
Binance public/read-only 数据和本地 Agent/thesis 上下文，可能产生网络/API/token
成本；启动前必须确认预算、代理和运行目的。

```bash
bash .github/scripts/start-auto-paper.sh ops-check --json
bash .github/scripts/start-auto-paper.sh start --json
bash .github/scripts/start-auto-paper.sh status --json
bash .github/scripts/start-auto-paper.sh stop --json
```

运行态写入 ignored `.github/.runtime/auto-paper/`。不要把运行日志、账本、SQLite audit journal、PID 文件或缓存提交到 Git。
常驻事实源默认是 `.github/.runtime/auto-paper/paper_ledger.json` 与 `.github/.runtime/auto-paper/cycles.jsonl`。
单轮 public-readonly/paper cycle 默认受 `TRADECAT_AUTO_PAPER_CYCLE_TIMEOUT_SECONDS=6000` 限制，避免进程仍在但心跳长期停滞。
启动脚本默认不生成 ignored `.github/.runtime/auto-paper/paper_autonomy_profile.json`，
缺少 Agent/Hermes 显式 `agent_trade_thesis.v1` 或显式 profile 时必须
fail-closed。只有设置 `TRADECAT_AUTO_PAPER_AUTONOMY_ENABLED=1` 或传入
`TRADECAT_AUTO_PAPER_AUTONOMY_PROFILE_PATH`，才允许使用 paper-only runtime profile。
用户后续要限制仓位、杠杆、退出或组合风险时，再显式传入 profile/policy。

启动脚本也默认运行 `strategy-review` 并写入 ignored `.github/.runtime/auto-paper/strategy_state.json`。该状态根据本地 paper outcome 自动暂停亏损 symbol、亏损信号类型或亏损方向，并限制最大 open positions 与单币并发；设置 `TRADECAT_AUTO_PAPER_STRATEGY_REVIEW_ENABLED=0` 可关闭这层 paper/watch 自我迭代过滤。

长期常驻不是默认模式。确需常驻时，使用 user systemd service 作为唯一生命周期 owner：

```bash
bash .github/scripts/start-auto-paper.sh systemd-install --json
systemctl --user status tradecat-auto-paper.service
```

该安装入口会禁用旧版 `tradecat-auto-paper.timer`，停止已有手动 `_run`，再启用长驻
`tradecat-auto-paper.service`。不要同时让 timer `_cycle` 和手动 `_run` 写同一套
`.github/.runtime/auto-paper/`。

## Web 监控

```bash
python3 .github/scripts/serve-auto-paper-monitor.py --host 127.0.0.1 --port 8765
```

打开 `http://127.0.0.1:8765/`。页面只读展示本地 paper/watch、审计日志、账本、输入信号、Agent decision text 和依赖链健康；它不会启动 auto-paper loop。

## 环境配置

参考 `.env.example`。允许配置 public 网络代理和本地 runtime 路径；不允许配置 Binance key、secret、listen key、账户 ID、真实下单或签名请求。

## 健康检查

```bash
bash .github/scripts/start-auto-paper.sh status --json
bash .github/scripts/run-tradecat.sh health-report --json
bash .github/scripts/run-tradecat.sh paper-report --json
bash .github/scripts/run-tradecat.sh latest-cycle --json
bash .github/scripts/run-tradecat.sh latest-decision --json
bash .github/scripts/run-tradecat.sh audit-journal --json
python3 .github/scripts/ops-audit.py --json
```

`ops-audit.py` 只读检查 auto-paper 状态、旧 systemd unit/drop-in、tmux pane、残留进程、
监控端口、crontab、runtime owner 和 ignored runtime autonomy profile。CI 只证明代码和门禁通过，
不代表本机 loop 正在运行。

## 发布前门禁

```bash
bash .github/scripts/agent-smoke.sh
bash .github/scripts/verify.sh
bash .github/scripts/validate-skill.sh --strict
bash .github/scripts/security-scan.sh
bash .github/scripts/supply-chain-audit.sh
git diff --check
```

如果要发布 tag，先更新 `CHANGELOG.md`，确认版本号与 `pyproject.toml` 一致，再创建 `vMAJOR.MINOR.PATCH` tag。
