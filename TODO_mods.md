# TradeCat 修改待办（独立版）

标记规范：`[状态] 优先级/复杂度 | 任务ID | 摘要 | 主要修改点 | 依赖`
- 状态：TODO / DOING / DONE
- 优先级：P0=阻断，P1=高，P2=中，P3=低
- 复杂度：L=低，M=中，H=高（按实现工作量和验证成本）

## 低复杂度（L）
- [TODO] P0/L | TC-01 | 移除硬编码 SQLite 路径 | `services/trading-service/config/.env.example` 改为相对路径，校验加载逻辑 | 无
- [TODO] P1/L | TC-02 | 统一 Bot 环境变量名 | `services/telegram-service/config/.env.example` + `src/bot/app.py` 仅保留 `TELEGRAM_BOT_TOKEN` | TC-01
- [TODO] P3/L | TC-03 | 精细化异常捕获 | `services/trading-service/src/simple_scheduler.py` 等去除裸 except，记录堆栈 | 无
- [TODO] P3/L | TC-04 | 注释语言统一中文 | `services/telegram-service/src/bot/app.py` 文本修订 | 无
- [TODO] P3/L | TC-05 | 币种黑名单移配置 | 将 `blocked_symbols` 提到配置/常量文件，加载时读取 | 无
- [TODO] P3/L | TC-06 | Magic Numbers 汇总 | 将分散常量集中到配置或常量模块 | 无
- [TODO] P3/LM | TC-07 | 增加 /health 健康检查 | 每个服务新增轻量接口或脚本自检 | 无

## 中等复杂度（M）
- [TODO] P0/M | TC-08 | 锁定依赖版本 | 固定各服务 `requirements.txt` 版本或生成 lock 文件，验证兼容性 | TC-01
- [TODO] P1/M | TC-09 | SQLite 并发写入防护 | 启用 WAL 或轻量连接池；评估写入路径 | TC-01
- [TODO] P1/MH | TC-10 | TimescaleDB 查询性能优化 | 为 `candles_5m` 创建复合索引/CA，回归查询性能 | 无
- [TODO] P3/MH | TC-11 | 日志配置统一 | 设计全局 `logging.config.dictConfig`，应用到各服务入口 | 无

## 高复杂度（H）
- [TODO] P2/H | TC-12 | 配置中心/统一加载 | 评估 python-dotenv 统一加载或接入配置中心服务 | TC-08
- [TODO] P2/H | TC-13 | 依赖/虚拟环境整合 | 评估 Poetry/uv，重建共享环境并验证各服务 | TC-08
- [TODO] P3/H | TC-14 | SQLite 体积治理 | 制定压缩/归档或迁移 TimescaleDB 方案，含数据迁移计划 | TC-09
- [TODO] P3/H | TC-15 | 服务间通信解耦 | 以 MQ 替代共享 SQLite，重新设计数据流 | TC-10
- [TODO] P3/H | TC-16 | 监控与告警接入 | Prometheus/Grafana/告警规则与部署 | TC-10
- [TODO] P3/H | TC-17 | 文档补齐 | API/部署/排障文档与生成流水线（Swagger/OpenAPI） | 其他任务完成后收敛

## 说明
- 任务顺序已按复杂度从低到高排列，便于快速落地与并行推进。
- 若执行顺序需要按业务优先级调整，可在状态列直接更新，无需改编号。

---

TradeCat 项目深度分析报告    根据代码审查，我发现以下需要优化的问题：

---

🔴 高优先级问题

1. 代码重复 - 硬编码数据库路径
位置: services/trading-service/config/.env.example:8
INDICATOR_SQLITE_PATH=/home/lenovo/.projects/tradecat/libs/database/services/telegram-service/market_data.db
问题: 硬编码绝对路径，项目迁移或部署时会失败
建议: 改为相对路径 ${PROJECT_ROOT}/libs/database/services/telegram-service/market_data.db

---

2. 缺少依赖版本锁定
位置: 所有 requirements.txt 文件
# 当前
psycopg[binary,pool]>=3.1.0
aiohttp>=3.9.0

# 应该
psycopg[binary,pool]==3.1.18
aiohttp==3.9.3
问题: 缺少版本锁定导致依赖漂移，可能导致不兼容
建议: 生成 requirements.lock.txt 或固定具体版本号

---

3. Bot 环境变量命名不一致
位置: services/telegram-service/config/.env.example:9,260
# .env.example 中
BOT_TOKEN=your_bot_token_here

# app.py:259 中
BOT_TOKEN = _require_env('BOT_TOKEN', required=True)
TELEGRAM_BOT_TOKEN = BOT_TOKEN  # 为了兼容性添加别名
问题: 同时使用 BOT_TOKEN 和 TELEGRAM_BOT_TOKEN，容易混淆
建议: 统一使用 TELEGRAM_BOT_TOKEN，废弃别名

---

4. 数据库查询缺少索引优化
位置: services/trading-service/src/simple_scheduler.py:90-136
sql = """
    WITH base AS (
   SELECT symbol,
SUM(quote_volume) as total_qv,
AVG((high-low)/NULLIF(close,0)) as volatility
   FROM market_data.candles_5m
   WHERE bucket_ts > NOW() - INTERVAL '24 hours'
   GROUP BY symbol
    ),
    ...
"""
问题: 大数据量时 GROUP BY 性能差，缺少复合索引
建议:
- 添加索引 CREATE INDEX ON candles_5m(symbol, bucket_ts DESC)
- 使用 TimescaleDB 的 continuous aggregates 预聚合数据

---

5. SQLite 并发写入风险
位置: services/trading-service/src/simple_scheduler.py:220-232
def get_indicator_latest(interval: str) -> datetime:
    try:
   conn = sqlite3.connect(SQLITE_PATH)
   row = conn.execute(...).fetchone()
   conn.close()
   return ...
问题: 多线程同时写入 SQLite 可能导致 "database is locked"
建议: 使用连接池或 SQLite 的 WAL 模式

---

🟡 中优先级问题

6. 配置分散，缺少统一配置中心
现状:
- config/.env - 公共配置
- services/*/config/.env.example - 各服务私有配置
- 每个服务单独加载自己的 .env

问题: 配置变更需要同步修改多个文件，容易遗漏
建议:
- 实现配置中心服务
- 或使用 python-dotenv 统一管理

---

7. 虚拟环境占用磁盘空间大
现状:
40M  telegram-service/.venv
154M order-service/.venv
174M data-service/.venv
206M trading-service/.venv
合计: 574MB
问题: 4 个虚拟环境重复安装相同依赖（aiohttp, requests 等）
建议: 考虑使用 Poetry 或 uv 管理虚拟环境，实现依赖共享

---

8. 日志配置分散
位置: 多处日志配置
# telegram-service/src/bot/app.py:26-29
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# trading-service/src/simple_scheduler.py:46-47
def log(msg: str):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)
问题: 日志格式不统一，缺少结构化日志
建议: 统一使用 logging.config.dictConfig

---

9. 错误处理过于宽泛
位置: 多处使用裸 except
# simple_scheduler.py:136,184,215,231
except Exception as e:
    log(f"K线优先级查询失败: {e}")
except:
    return None
问题: 隐藏了具体错误类型，难以调试
建议: 捕获具体异常类型，并添加 exc_info=True 记录堆栈

---

10. 缺少 API 健康检查端点
问题: 所有服务都没有健康检查接口
影响: 无法使用 Kubernetes/K8s 或 Docker healthcheck
建议: 为每个服务添加 /health 端点

---

🟢 低优先级优化

11. 代码注释混合中文和英文
位置: telegram-service/src/bot/app.py
# ================== 本地 .env 加载 ==================
# 数据文件配置 - 使用项目根目录下的data文件夹
# ================== 简化权限检查 ==================
建议: 统一使用中文注释（符合项目规范）

---

12. 硬编码的币种过滤
位置: telegram-service/src/bot/app.py:779,779,
self.blocked_symbols = {'BNXUSDT', 'ALPACAUSDT'}
建议: 移到配置文件中

---

13. 缺少单元测试
现状: 只有 scripts/verify.sh 做语法检查
建议: 为核心模块添加单元测试（pytest）

---

14. Magic Numbers
位置: 多处
# app.py:288
CLICK_COOLDOWN_SECONDS = 0.1

# simple_scheduler.py:32
HIGH_PRIORITY_TOP_N = 50
建议: 已提取为常量，但建议集中到配置文件

---

15. SQLite 数据库文件过大
现状: market_data.db 大小为 303MB
建议: 定期压缩或使用 TimescaleDB 替代

---

📊 架构层面建议

16. 服务间通信缺失
现状: 服务间通过共享 SQLite 文件通信
问题: 紧耦合，无法分布式部署
建议: 引入消息队列实现异步通信

---

17. 缺少监控和告警
建议:
- 集成 Prometheus + Grafana
- 添加关键指标监控（数据延迟、计算时间、错误率）

---

18. 文档不完整
缺失:
- API 文档
- 部署文档
- 故障排查指南
建议: 使用 Swagger/OpenAPI 生成 API 文档

---

🎯 优化优先级排序

| 优先级 | 问题 | 影响范围 | 修复难度 |
|:---:|:---|:---|:---:|
| P0 | #1 硬编码路径 | 部署/迁移 | 低 |
| P0 | #2 依赖版本 | 生产环境稳定性 | 中 |
| P1 | #4 数据库查询 | 性能 | 中 |
| P1 | #5 SQLite 并发 | 数据完整性 | 中 |
| P1 | #3 变量命名一致性 | 维护性 | 低 |
| P2 | #6 配置管理 | 可维护性 | 高 |
| P2 | #7 虚拟环境 | 资源占用 | 高 |
| P3 | #8 日志统一 | 可观测性 | 中 |
| P3 | #9 错误处理 | 可调试性 | 低 |
| P3 | #10 健康检查 | 部署 | 低 |

---

💡 架构重构建议（长期）

1. 微服务化: 拆分为独立可部署的服务
2. API 网关: 统一入口，处理认证、限流
3. 服务注册发现: 使用 Consul/Etcd
4. 配置中心: 使用 Apollo/Nacos
5. 链路追踪: 集成 Jaeger/Zipkin

• - 低复杂度：
      - 代码格式调整（依赖最少，易实施）
      - 变量命名规范化（简单修改，无逻辑改动）
  - 中等复杂度：
      - 添加状态管理（需调整数据流，有一定依赖关系）
      - 实现基本界面交互（涉及事件响应，依赖状态数据）
  - 高复杂度：
      - 业务逻辑重构（影响面广，依赖多模块）
      - 性能优化（需分析瓶颈，修改核心流程）
      - 引入异步处理（复杂数据依赖和回调管理）

  任务间存在依赖，如状态管理需先于界面交互，业务逻辑重构影响性能优化方案。

• 按“实现复杂度（工作量、变更面、验证成本）”由低到高排序，并给出简短理由：

  - #1 硬编码路径 → 低：改 env 模板/加载逻辑即可，回归测试很小。
  - #3 Bot 环境变量统一 → 低：重命名一处配置与引用，验证启动即可。
  - #9 错误处理细化 → 低：替换裸 except，加日志；不改功能。
  - #11 注释语言统一 → 低：文本修饰，无行为变化。
  - #12 币种过滤移配置 → 低：提到配置文件，改一处读取。
  - #14 Magic Numbers 汇总 → 低：集中常量或配置，影响面小。
  - #10 健康检查端点 → 低-中：每服务加一个轻量 /health，少量路由与测试。
  - #2 依赖版本锁定 → 中：需锁版本/生成 lock，验证所有服务依赖兼容性。
  - #5 SQLite 并发风险 → 中：启用 WAL 或简单连接池，需并发表现回归。
  - #4 TimescaleDB 查询索引/预聚合 → 中-高：新增索引/CA，需要数据库变更与性能验证。
  - #8 日志统一 → 中-高：设计全局 logging 配置，改多服务入口，需观察格式一致性。
  - #6 配置中心/统一加载 → 高：引入新组件或改加载路径，回归所有服务配置。
  - #7 虚拟环境合并（Poetry/uv） → 高：重组依赖管理，重新安装/验证全局。
  - #15 SQLite 体积治理 → 高：涉及迁移/压缩或改用 TimescaleDB，需数据迁移验证。
  - #16 服务间通信改 MQ → 高：架构级改动，重写数据流与部署。
  - #17 监控与告警 → 高：接入 Prometheus/Grafana/告警链路，需运维支持。
  - #18 文档补齐（API/部署/排障） → 高：跨团队信息收集与编写，持续维护。