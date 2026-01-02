# 2026-01-03T04:07:32+08:00 代码审计报告核实
- 任务范围：对用户提供的代码审计摘要逐项与当前仓库源码比对，核实风险点与修复建议。
- 关键发现：
  - 启动脚本 `services/*/scripts/start.sh` 均直接 `source config/.env`，存在环境变量注入风险。
  - `telegram-service/src/signals/` 目录已存在且全局未发现 `from signal` 旧引用，重命名兼容性风险低。
  - `telegram-service/src/cards/data_provider.py` 的最新时间戳去重逻辑使用字符串比较，存在格式差异导致排序错误的潜在风险。
  - 币种白名单读取未做格式校验，仍可能被注入非法符号。
  - data-service 默认代理端口在代码中硬编码为 `http://127.0.0.1:9910`，缺少可用性检测或配置化验证。
- 涉及文件：
  - services/data-service/scripts/start.sh
  - services/trading-service/scripts/start.sh
  - services/telegram-service/scripts/start.sh
  - services/telegram-service/src/cards/data_provider.py
  - services/data-service/src/config.py
- 验证：未执行自动化测试，仅通过源码静态审阅与 `rg` 搜索确认。
- 遗留/下一步：
  - 将 `.env` 加载改为安全解析（例如 `set -a; export $(grep -v '^#' .env | xargs -d '\n'); set +a` 或使用 `python -m dotenv`），并添加用例验证。
  - 为 SYMBOLS_* 配置添加正则校验及单测；将时间戳比较改为 datetime 对象。
  - 评估代理端口配置化与健康检查需求。

# 2026-01-03T04:12:00+08:00 新增待办清单
- 任务范围：整理性能/成本优化方向的详细 TODO。
- 关键内容：新增 `TODO.md`，覆盖 .env 安全加载、代理自检、批量拉取/计算、执行器拆分、SQLite 连接池、时间戳比较、符号校验、Timescale 压缩、日志轮转等项目，按难度排序。
- 涉及文件：
  - TODO.md: 新增待办列表
- 验证：仅文档更新，未改动业务代码。
- 遗留/下一步：按优先级推进 TODO 执行，落地后补充测试与文档。

# 2026-01-03T04:50:50+08:00 验收/审计标准
- 任务范围：为优化待办生成逐项验收与审计标准。
- 关键内容：新增 `AUDIT_CHECKLIST.md`，定义每项的开发自检与独立审计要点（日志轮转、.env 安全加载、符号校验、时间戳解析、代理自检、SQLite 连接池、IO/CPU 拆分、批量拉取/计算、Timescale 压缩）。
- 涉及文件：
  - AUDIT_CHECKLIST.md: 新增审计标准
- 验证：未改动业务逻辑，仅文档补充。
- 遗留/下一步：实施对应 TODO 时按该清单逐项验收，并在变更中引用。

# 2026-01-03T05:01:01+08:00 TODO 与审计合并
- 任务范围：将待办与验收/审计标准合并为单一文档。
- 关键内容：删除独立 AUDIT_CHECKLIST；重写 `TODO.md`，在每项任务下直接列动作、验收、审计要点，保持难度排序与完成状态。
- 涉及文件：
  - TODO.md: 重写，合并审计要点
  - AUDIT_CHECKLIST.md: 已移除
- 验证：仅文档结构调整，无业务代码变更。
- 遗留/下一步：执行 TODO 时按内嵌验收/审计要点完成并记录。

# 2026-01-03T05:05:09+08:00 新增独立验收/审计清单
- 任务范围：按用户要求恢复独立的验收/审计文档，并保持与 TODO 清单同步。
- 关键内容：新增 `AUDIT_CHECKLIST.md`，详细列出 9 项优化任务的验收标准与审计要点（日志轮转、.env 安全、符号校验、时间戳解析、代理自检、SQLite 连接池、IO/CPU 拆分、批量拉取/计算、Timescale 压缩）。
- 涉及文件：
  - AUDIT_CHECKLIST.md: 新增
  - TODO.md: 保持现状（动作+验收/审计要点）
- 验证：仅文档新增，无业务代码改动。
- 遗留/下一步：执行任务时两处文档需同步勾选状态与记录。

2026-01-03T05:17:02+08:00 | 创建独立修改待办清单
- 关键改动：新增 `TODO_mods.md`，按复杂度/优先级列出整改任务，含状态/依赖字段。
- 涉及文件：TODO_mods.md
- 验证：文件新增，格式为 Markdown，人工检查无语法风险。
- 遗留/下一步：后续执行任务时更新状态列并在完成时补充验证结果。
