# TradeCat Public

## Sponsors / 赞助商

| Sponsor | Link |
|---|---|
| CA（交易猫 tradecat 社区） | [`0x8a99b8d53eff6bc331af529af74ad267f3167777`](https://dexscreener.com/bsc/0x8a99b8d53eff6bc331af529af74ad267f3167777) |
| OPENAI | [OpenAI](https://openai.com/) |

项目调整中，目前本地cli使用渠道暂不可用，请跳转至web端使用

https://docs.google.com/spreadsheets/d/1k16nGFCE7oBXrEqvTpHSA2Z5530GM_kou-wiWklTsfY/edit?gid=358741612#gid=358741612

TradeCat Public 的目标形态是一个可被 Hermes、Codex、Claude Code、OpenClaw 等 Agent 框架驱动的自主交易 loop：先通过公开在线表格信号感知市场异动，后续可扩展其他信号源；再由 Agent 通过 tools、skills、Binance API 文档和 public/read-only 行情数据自主补全上下文，形成 USDT 本位合约的交易 thesis、纸面回测、交易决策、订单/仓位管理、结果归因，并基于历史执行数据持续复盘和自我迭代。

当前公开仓库实现的是这个目标形态中的 public-readonly + paper/watch 层：公开在线表格只作为信号源；Agent/Hermes 根据仓库内自包含的 Binance skill/API 快照和公开只读工具补齐行情上下文与交易 thesis；TradeCat 负责 schema 审计、信号对齐、paper/watch 执行、账本、风控拒绝、报告和可复现审计。

本仓库的核心目标是：Agent 交易员同步在线表格作为信号源的自主纸面交易系统。旧的本地交互式 TUI、安装器、watchdog、缓存浏览器和 `project/` 根目录已经退役。

仓库身份以 `tradecat-public` 为准；GitHub remote 为 `tukuaiai/tradecat-public`。本仓库不代表旧私有 TradeCat 运行态，也不包含实盘 executor。

## 功能特性

- 读取公开在线表格 `signal_flow` 和 `anomaly_panel`，不依赖私有 TradeCat 服务端。
- 使用 `.github/contracts/` 中的 JSON Schema 约束在线表格 source payload、Agent market context、trade thesis、paper report、audit journal 等 I/O。
- 保留 Binance public-readonly skill/API 快照与 provenance，供 Agent/Hermes 研究行情上下文。
- 执行本地 paper/watch，不读取 Binance key，不签名，不访问账户/订单私有端点，不真实下单。
- 缺少 Agent 明确 sizing、leverage、stop loss、take profit 或 max holding plan 时 fail-closed。
- 默认不常驻运行；paper loop 和 Web monitor 都必须由操作员显式启动。
- 运行态隔离在 ignored `.github/.runtime/`，可生成 paper ledger、cycle archive、SQLite audit journal、health/daily/replay/alert 报告。
- 内嵌 `.github/skills/tradecat-public/`，Agent/Hermes 可按 manifest 和 Skill references 使用本仓库。

## 安全边界

- 只允许 public/read-only market data 与本地 paper/watch。
- 禁止读取 Binance key/secret、`.env`、listen key、账户、余额、真实持仓或订单。
- 禁止签名请求，禁止调用下单、撤单、改杠杆、改保证金等私有端点。
- 禁止真实下单；实盘 executor 必须是未来独立私有仓库。
- 本地运行态只能写入 ignored `.github/.runtime/`、`.tradecat/`、`.github/.venv/`、`.github/.tools/`、`.github/.hermes/`。
- 交易 sizing、leverage、止损、止盈、持仓时长必须来自 Agent thesis 或 ignored runtime paper autonomy profile；TradeCat 不写入真实交易参数。

## 快速开始

环境要求来自 `pyproject.toml` 和 CI：

- Python `>=3.12`；CI 覆盖 Python `3.12` 和 `3.13`。
- `pip`。
- 可选：`make`、Docker 或本地 `gitleaks`，用于部分开发入口或安全扫描加速。

安装开发依赖：

```bash
python3 -m pip install -c constraints.txt -e ".[dev]"
```

最短只读检查：

```bash
python3 .github/scripts/request.py --datasets --format json
python3 .github/scripts/request.py signal_flow --format json --limit 5
python3 .github/scripts/request.py anomaly_panel --format json --limit 0
bash .github/scripts/run-tradecat.sh soft-layer --json
bash .github/scripts/start-auto-paper.sh status --json
```

如需代理读取公开在线表格，使用标准环境变量：

```bash
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
```

## 干净 Hermes 容器

WSL2 Ubuntu 内可用 Docker 时，推荐用独立 Ubuntu 服务容器运行 Hermes + TradeCat，
避免宿主 `~/.hermes` 的旧会话、旧技能、旧 gateway 状态和其他项目数据污染当前 Agent loop。
该容器不会挂载宿主 `~/.hermes`、`~/.codex` 或宿主项目目录；镜像内包含完整仓库种子，
启动时复制到独立 `tradecat_project` volume。Hermes home、Codex home、TradeCat venv 和
paper runtime 也都在独立 Docker volume 中。

```bash
cp .github/docker/tradecat-hermes-clean/container.env.example .github/docker/tradecat-hermes-clean/container.env
bash .github/scripts/tradecat-hermes-container.sh build
bash .github/scripts/tradecat-hermes-container.sh up
bash .github/scripts/tradecat-hermes-container.sh verify
```

进入容器后项目位置是 `/workspace/tradecat-public`，这是容器自己的项目副本，不是宿主
bind mount。需要从镜像种子重置它时运行
`bash .github/scripts/tradecat-hermes-container.sh refresh-project`。

容器默认只保持空闲常驻，不自动启动 Telegram gateway，也不自动启动 paper loop。
Telegram token、OpenAI key 和代理只写入 ignored
`.github/docker/tradecat-hermes-clean/container.env`，不要写入 Git。详细说明见
`.github/docker/tradecat-hermes-clean/README.md` 与 `.github/docs/deployment.md`。
HexHub/SSH 进入时填 `Host=127.0.0.1`、`Port=2222`、`User=ubuntu`、`Password=ubuntu`。

## 目录结构

```text
tradecat-public/
|-- README.md
|-- AGENTS.md
|-- CONTRIBUTING.md
|-- CHANGELOG.md
|-- LICENSE
|-- pyproject.toml
|-- constraints.txt
|-- Makefile
|-- .env.example
|-- compose.tradecat-hermes.yml # WSL2 内干净 Hermes/TradeCat Ubuntu 容器
`-- .github/
    |-- CODEOWNERS
    |-- dependabot.yml
    |-- pull_request_template.md
    |-- workflows/ci.yml
    |-- contracts/                 # JSON Schema 机器契约
    |-- docs/                      # 架构、配置、部署、发布说明
    |-- docker/                    # 本地隔离运行环境
    |-- resources/
    |   |-- agent_market_context/  # Binance skill/API 只读快照与 provenance
    |   `-- agent_soft_layer/      # Agent 角色与软策略资源
    |-- scripts/                   # request、paper runtime、验证、监控入口
    |-- src/
    |   |-- tradecat_sources/      # 在线表格公开信号源读取与 dataset contract
    |   `-- tradecat_auto/         # Agent context、paper/watch、ledger、风控、报告
    |-- tests/
    `-- skills/tradecat-public/    # Hermes/Codex Skill 包
```

`.github/skills/tradecat-public/agents/manifest.json` 是 Agent/Hermes 的唯一机器主契约。文档只解释它，不复制第二份机器契约。

`project/` 已退役；`.github/tasks/` 是本地任务拆解/草稿目录，和 `.github/.runtime/` 一样不进入公开 GitHub 仓库。

## 配置说明

配置示例见 `.env.example`。允许的本地配置：

```text
HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=127.0.0.1,localhost
TRADECAT_AUTO_PAPER_RUNTIME_DIR=.github/.runtime/auto-paper
TRADECAT_AUTO_PAPER_CYCLE_TIMEOUT_SECONDS=6000
TRADECAT_AUTO_PAPER_FEE_BPS=4
TRADECAT_AUTO_PAPER_SLIPPAGE_BPS=0
TRADECAT_AUTO_PAPER_AGENT_TRADE_THESIS_PATH=
TRADECAT_AUTO_PAPER_AUTONOMY_ENABLED=0
TRADECAT_AUTO_PAPER_AUTONOMY_PROFILE_PATH=
TRADECAT_AUTO_PAPER_AUTONOMY_MARGIN_USDT=10
TRADECAT_AUTO_PAPER_AUTONOMY_LEVERAGE=1
TRADECAT_AUTO_PAPER_AUTONOMY_STOP_LOSS_BPS=150
TRADECAT_AUTO_PAPER_AUTONOMY_TAKE_PROFIT_BPS=300
TRADECAT_AUTO_PAPER_AUTONOMY_MAX_HOLDING_MINUTES=90
TRADECAT_AUTO_PAPER_AUTONOMY_DIRECTION_POLICY=sheet_signal_or_taker_flow
TRADECAT_AUTO_PAPER_MONITOR_HOST=127.0.0.1
TRADECAT_AUTO_PAPER_MONITOR_PORT=8765
```

默认本地 Web 监控地址来自 `.github/scripts/serve-auto-paper-monitor.py`：`http://127.0.0.1:8765/`。

`start-auto-paper.sh` 默认是手动运行 + 外部 Agent thesis 模式，不会自动生成
`.github/.runtime/auto-paper/paper_autonomy_profile.json`，缺少明确 sizing/exits 时继续
`agent_sizing_required` fail-closed。只有显式设置 `TRADECAT_AUTO_PAPER_AUTONOMY_ENABLED=1`
或传入 `TRADECAT_AUTO_PAPER_AUTONOMY_PROFILE_PATH` 时，才会使用 paper-only runtime profile。

`start-auto-paper.sh` 也会默认维护 ignored `.github/.runtime/auto-paper/strategy_state.json`。
该状态由 `strategy-review` 基于本地 paper ledger / cycle archive 生成，用于把亏损
symbol、亏损信号类型、亏损方向、最大持仓数和单币并发上限反馈到下一轮 paper 风控。
这是本地 paper/watch 自我迭代过滤，不读取 Binance 凭证，也不会触发真实订单。

纸面成本模型默认使用 Binance USDⓈ-M 官方 commission-rate 文档示例中的 taker 费率 `4 bps`
作为 public fallback；实际开仓滑点优先用公开 `/fapi/v1/depth` 盘口按 Agent notional
估算成交均价。精确账户/VIP/symbol 费率需要签名 `USER_DATA`，不属于本公开仓库边界。

TODO: GitHub 仓库 Settings 中的 `main` 分支保护、必需 review 和必需 status checks 无法从仓库文件确认；需要仓库管理员在 GitHub UI/API 中核查。

## Agent 纸面交易流

```text
signal_flow / anomaly_panel
-> Agent/Hermes 读取 Binance public/read-only K线、盘口、资金费率、OI 等上下文
-> agent_market_context.v1 + agent_trade_thesis.v1
-> context-audit
-> run-context / run-loop
-> paper risk gate
-> paper ledger + cycle archive + audit journal
-> health / daily / alert / replay report
```

常用 paper/watch 命令：

```bash
bash .github/scripts/binance-public-bundle.sh --symbols BTCUSDT,ETHUSDT --json
bash .github/scripts/run-tradecat.sh agent-market-context --symbol BTCUSDT --json
bash .github/scripts/run-tradecat.sh context-audit --input context.json --json
bash .github/scripts/run-tradecat.sh run-context --input context.json --mode paper --json
bash .github/scripts/run-tradecat.sh run-once --agent-trade-thesis-path thesis.json --mode paper --json
bash .github/scripts/run-tradecat.sh paper-report --json
bash .github/scripts/run-tradecat.sh strategy-review --ledger-path .github/.runtime/auto-paper/paper_ledger.json --archive-path .github/.runtime/auto-paper/cycles.jsonl --json
bash .github/scripts/run-tradecat.sh latest-cycle --json
bash .github/scripts/run-tradecat.sh latest-decision --json
bash .github/scripts/run-tradecat.sh audit-journal --json
bash .github/scripts/run-tradecat.sh health-report --json
bash .github/scripts/run-tradecat.sh daily-report --json
```

缺少 Agent sizing/exits 时，TradeCat 必须 fail-closed，并返回结构化 `error_code`，不得自动填金额、杠杆、止损或止盈。

## 常驻 paper/watch

默认不要常驻运行。启动 loop 会持续读取在线表格、public Binance 数据和本地 Agent/thesis
上下文，可能带来网络/API/token 成本；启动前先确认预算、代理和运行目的。

```bash
bash .github/scripts/start-auto-paper.sh ops-check --json
bash .github/scripts/start-auto-paper.sh start --json
bash .github/scripts/start-auto-paper.sh status --json
bash .github/scripts/start-auto-paper.sh stop --json
```

长期常驻用 user systemd service 作为唯一生命周期 owner：

```bash
bash .github/scripts/start-auto-paper.sh systemd-install --json
systemctl --user status tradecat-auto-paper.service
```

`systemd-install` 会禁用旧版 `tradecat-auto-paper.timer`，停止已有手动 `_run`，
再启用长驻 `tradecat-auto-paper.service`；不要让 timer `_cycle` 和手动 `_run`
同时写 `.github/.runtime/auto-paper/`。

本地 Web 监控页面：

```bash
python3 .github/scripts/serve-auto-paper-monitor.py --host 127.0.0.1 --port 8765
```

页面只读展示本地 paper/watch、审计日志、账本、输入信号、Agent decision text 和依赖链健康，
不会启动 auto-paper loop，不接触真实账户。

## 常用命令

```bash
# 安装
python3 -m pip install -c constraints.txt -e ".[dev]"
make install-dev

# 只读数据源
python3 .github/scripts/request.py --datasets --format json
python3 .github/scripts/request.py signal_flow --format json --limit 5
python3 .github/scripts/request.py anomaly_panel --format json --limit 0
bash .github/scripts/binance-public-snapshot.sh --symbols BTCUSDT,ETHUSDT --json

# 测试、lint、format
PYTHONPATH=.github/src python3 -m pytest -q
PYTHONPATH=.github/src ruff check .github/src .github/tests
PYTHONPATH=.github/src ruff format --check .github/src .github/tests .github/scripts

# 完整本地门禁
bash .github/scripts/agent-smoke.sh
bash .github/scripts/verify.sh
bash .github/scripts/validate-skill.sh --strict
bash .github/scripts/security-scan.sh
bash .github/scripts/supply-chain-audit.sh
python3 .github/scripts/validate_dependency_policy.py
python3 .github/scripts/validate_testing_ci_contract.py
python3 .github/scripts/ops-audit.py --json
git diff --check

# 构建 wheel，来源于 CI
python3 -m pip wheel . --no-deps -w /tmp/tradecat-wheel
```

`Makefile` 还提供 `make test`、`make lint`、`make format`、`make format-check`、`make test-ci-contract`、`make security`、`make supply-chain`、`make agent-smoke`、`make verify`、`make ops-audit`、`make paper-status`、`make paper-start`、`make paper-stop`、`make monitor`。

## CI/CD

CI 文件为 `.github/workflows/ci.yml`，触发条件包括 `push`、`pull_request`、`workflow_dispatch` 和每日定时任务。CI 执行：

- 最小权限 `permissions: contents: read`、同 ref 并发取消、job timeout、checkout 不持久化凭证。
- Skill strict validation。
- secret scan。
- 安装 `python -m pip install -c constraints.txt -e ".[dev]"`。
- public boundary guard。
- dependency policy。
- testing/CI contract validation，机器清单位于 `.github/resources/test_ci_matrix.json`，设计说明见 `.github/docs/testing-ci-strategy.md`。
- `ruff check .github/src .github/tests`。
- `ruff format --check .github/src .github/tests .github/scripts`。
- `PYTHONPATH=.github/src pytest -q`。
- data contract validators。
- supply-chain audit。
- shell/Python syntax check。
- wheel package data check。
- agent readiness smoke。

CI 只证明代码、契约、测试和安全门禁通过；它不证明本机 auto-paper loop 正在运行。

本仓库只提供本地开发/运行隔离用 Docker Compose，不提供生产 K8s manifest 或 Helm chart。
容器形态仍然只允许运行 public-readonly + paper/watch；不读取 Binance key，不签名，不真实下单。

## Troubleshooting / FAQ

- `ModuleNotFoundError: tradecat_auto`：先安装 `python3 -m pip install -c constraints.txt -e ".[dev]"`，或运行命令时设置 `PYTHONPATH=.github/src`。
- `ruff` 或 `pytest` 不存在：运行 `bash .github/scripts/bootstrap-dev.sh` 或安装开发依赖。
- 在线表格读取失败或 HTTP 404：先运行 `python3 .github/scripts/request.py --datasets --format json` 确认 dataset；如网络受限，设置 `HTTP_PROXY` / `HTTPS_PROXY`。
- `paper_service_not_running`：运行 `bash .github/scripts/start-auto-paper.sh status --json` 查看状态，需要常驻时运行 `bash .github/scripts/start-auto-paper.sh start --json`。
- `heartbeat_stale` 但 pid 仍在：说明单轮 public-readonly/paper cycle 可能卡住；`TRADECAT_AUTO_PAPER_CYCLE_TIMEOUT_SECONDS` 会限制单轮最长时间，必要时运行 `bash .github/scripts/start-auto-paper.sh heal --json`。
- `paper-report` 显示 0 仓但服务在交易：默认账本应为 `.github/.runtime/auto-paper/paper_ledger.json`；用 `bash .github/scripts/run-tradecat.sh latest-decision --json` 和 `bash .github/scripts/run-tradecat.sh health-report --json` 核对常驻服务事实源。
- `agent_sizing_required` 在重启后出现：这是默认 fail-closed 手动模式；需要 Agent/Hermes 显式写入 thesis，或明确设置 `TRADECAT_AUTO_PAPER_AUTONOMY_ENABLED=1` / `TRADECAT_AUTO_PAPER_AUTONOMY_PROFILE_PATH`。
- 想审计是否有旧服务、进程、端口或 cron 残留：运行 `python3 .github/scripts/ops-audit.py --json`。
- 想完全改 paper 自治参数：设置 `TRADECAT_AUTO_PAPER_AUTONOMY_*`，并显式打开 `TRADECAT_AUTO_PAPER_AUTONOMY_ENABLED=1`，或显式传入 `TRADECAT_AUTO_PAPER_AGENT_TRADE_THESIS_PATH` / `TRADECAT_AUTO_PAPER_AUTONOMY_PROFILE_PATH`。
- 监控端口冲突：使用 `python3 .github/scripts/serve-auto-paper-monitor.py --host 127.0.0.1 --port <free-port>`。

## 贡献指南

- 贡献流程：`CONTRIBUTING.md`
- 变更记录：`CHANGELOG.md`
- 架构说明：`.github/docs/ARCHITECTURE.md`
- 配置说明：`.github/docs/configuration.md`
- 部署与运维：`.github/docs/deployment.md`
- 运维 runbook：`.github/docs/operations-runbook.md`
- 发布流程：`.github/docs/release.md`

`.github/pull_request_template.md`、`.github/CODEOWNERS` 和 `.github/dependabot.yml` 提供 PR、review owner 与依赖更新入口。平台级分支保护需要在 GitHub 仓库设置中启用。
