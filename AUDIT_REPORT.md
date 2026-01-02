# 代码审计分析报告

**审计日期**: 2026-01-03  
**审计范围**: TradeCat 安全/稳定性优化变更  
**审计人**: AI Assistant

---

## 1. 摘要（Executive Summary）

### 审计输入来源
- 直接检视当前仓库代码（commit f0b11e7）
- 包含 9 项优化变更 + 审计修复

### 总体风险判断：**低**
- 主要安全风险已修复（.env 注入、权限检查、时间戳比较）
- 剩余风险为配置层面（服务级 .env 权限）和边缘场景

### 关键结论 Top 5
1. ✅ `.env` 加载已改为只读解析，阻断命令注入（确定）
2. ✅ 权限检查已改为硬失败，非 600 则退出（确定）
3. ✅ 代理检测已覆盖 HTTP_PROXY 和 HTTPS_PROXY（确定）
4. ✅ `fetch_base` 和 `fetch_metric` 均使用 datetime 比较（确定）
5. ⚠️ 服务级 `.env` 文件权限为 644，需修复为 600（确定）

### 需要立即确认/回滚
- **无回滚需求**
- 需立即修复：`services/*/config/.env` 权限改为 600

---

## 2. 审计范围与假设

### 2.1 范围
| 模块 | 文件 | 变更类型 |
|:---|:---|:---|
| 启动脚本 | `services/*/scripts/start.sh` | 安全加固 |
| 数据提供层 | `telegram-service/src/cards/data_provider.py` | 连接池+时间戳 |
| 计算引擎 | `trading-service/src/core/engine.py` | IO/CPU 拆分 |
| 数据库读写 | `trading-service/src/db/reader.py` | 批量优化 |
| 配置 | `config/.env.example`, `services/*/config/.env.example` | 模板更新 |
| 运维脚本 | `scripts/timescaledb_compression.sh` | 压缩管理 |

### 2.2 假设与不确定性声明
- 运行环境：WSL2 Ubuntu（已确认）
- 部署模式：单机多服务（非容器）
- 不确定性：生产环境是否与开发环境配置一致（低影响）

---

## 3. 变更解析（Change Breakdown）

| ID | 模块/文件 | 变更类型 | 安全相关性 | 理由 |
|:---|:---|:---|:---|:---|
| C1 | `start.sh::safe_load_env` | 修改 | 高→低 | 阻断 `export/$()/\`` 注入 |
| C2 | `start.sh::权限检查` | 修改 | 高 | 非 600 硬失败 |
| C3 | `start.sh::validate_symbols` | 新增 | 中 | 正则校验币种格式 |
| C4 | `start.sh::check_proxy` | 修改 | 中 | 覆盖 HTTP/HTTPS |
| C5 | `data_provider.py::_parse_timestamp` | 新增 | 中 | 统一时间戳解析 |
| C6 | `data_provider.py::fetch_base` | 修改 | 中 | 改用 datetime 比较 |
| C7 | `data_provider.py::_SQLitePool` | 新增 | 中 | 连接池+退出钩子 |
| C8 | `engine.py::_compute_parallel` | 修改 | 低 | IO/CPU 拆分 |
| C9 | `reader.py::write` | 修改 | 低 | executemany 批量 |
| C10 | TimescaleDB 压缩策略 | 配置 | 低 | 30天压缩，无删除 |

---

## 4. 威胁建模与攻击面变化

### 4.1 关键资产
- **进程环境**: 环境变量（含 API 密钥、数据库凭证）
- **数据库**: TimescaleDB（K线）、SQLite（指标）
- **网络出口**: 代理配置、Binance API 访问
- **日志**: 服务日志（可能含敏感信息）

### 4.2 攻击面变化
| 攻击面 | 变化 | 风险 |
|:---|:---|:---|
| .env 注入 | 已关闭 | ✅ 消除 |
| 权限绕过 | 硬失败 | ✅ 消除 |
| 代理探测 | 外呼 Binance | ⚠️ 可接受 |
| SQLite 并发 | 连接池 | ✅ 改善 |

### 4.3 权限模型
- 文件权限：`.env` 应为 600（当前服务级为 644）
- 进程权限：普通用户运行
- 数据库权限：读写分离（TimescaleDB 读，SQLite 写）

---

## 5. 审计发现（Findings）

### [Medium] 服务级 .env 文件权限不正确

- **严重级别**: Medium
- **置信度**: 高（已通过 stat 确认）
- **关联变更点**: C2（权限检查逻辑）
- **影响范围**: 3 个服务配置文件

**当前状态**:
```
644 services/data-service/config/.env
644 services/telegram-service/config/.env
644 services/trading-service/config/.env
```

**攻击路径**:
1. 同机其他用户可读取 .env 文件
2. 获取数据库凭证、API 密钥、Bot Token
3. 未授权访问数据库或冒充 Bot

**根因分析**: 权限检查逻辑正确，但文件创建时未设置正确权限

**修复建议**:
1. 立即执行: `chmod 600 services/*/config/.env`
2. 更新 `scripts/init.sh` 在复制 .env 时设置权限
3. 添加 CI 检查确保权限正确

**对应标准**: CWE-732 (Incorrect Permission Assignment)

---

### [Low] 代理探测目标固定为 Binance

- **严重级别**: Low
- **置信度**: 高
- **关联变更点**: C4
- **影响范围**: 启动阶段网络请求

**当前实现**:
```bash
curl -s --max-time 3 --proxy "$proxy" https://api.binance.com/api/v3/ping
```

**潜在风险**:
- 探测目标固定，无法适应其他交易所
- 3 秒超时可能在网络慢时误判

**修复建议**:
1. 可配置探测 URL: `PROXY_TEST_URL`
2. 超时可配置: `PROXY_TEST_TIMEOUT`
3. 当前实现可接受，优先级低

---

### [Low] _parse_timestamp 丢弃时区信息

- **严重级别**: Low
- **置信度**: 高
- **关联变更点**: C5
- **影响范围**: 时间戳比较

**当前实现**:
```python
if '+' in ts_str:
    ts_str = ts_str.split('+')[0]
```

**潜在风险**:
- 不同时区的时间戳被当作同一时区比较
- 实际场景：数据源均为 UTC，风险极低

**修复建议**:
1. 当前实现可接受（数据源统一）
2. 长期：统一使用 aware datetime

---

### [Info] SQLite 连接池在多进程模式下的使用

- **严重级别**: Info
- **置信度**: 中
- **关联变更点**: C7
- **影响范围**: 进程模式计算

**当前实现**:
- 连接池使用 `check_same_thread=False`
- 已注册 `atexit` 退出钩子

**注意事项**:
- 多进程模式下，子进程会继承父进程的连接池
- SQLite 连接不应跨进程共享
- 当前 telegram-service 为单进程，无风险

**建议**:
- 在 `_get_pool` 中检查 PID，跨进程时重建池
- 当前可接受，优先级低

---

## 6. 回归风险与安全测试计划

### 6.1 回归风险清单
| 模块 | 风险 | 测试方法 |
|:---|:---|:---|
| 启动脚本 | 权限检查误杀 | 测试 600/644/400 权限 |
| 代理检测 | 误禁用代理 | 测试好/坏代理场景 |
| 时间戳比较 | 排序错误 | 混合格式数据测试 |
| 连接池 | 连接泄漏 | 压力测试 + 监控句柄 |

### 6.2 必测用例
```bash
# 1. .env 注入测试
echo "TEST=\$(whoami)" >> config/.env
./scripts/start.sh start  # 应不执行命令

# 2. 权限检查测试
chmod 644 config/.env
./scripts/start.sh start  # 应退出

# 3. 代理测试
HTTP_PROXY=http://bad:1234 ./scripts/start.sh start  # 应禁用代理

# 4. 时间戳测试
# 混合格式: "2026-01-01T00:00:00Z", "2026-01-01 00:00:00", "2026-01-01T00:00:00+08:00"
```

### 6.3 自动化建议
- [ ] 添加启动脚本单元测试
- [ ] 添加 data_provider 时间戳测试
- [ ] CI 中检查 .env 权限

---

## 7. 依赖/配置/部署审计

### 7.1 依赖
- 未新增外部依赖
- 使用标准库: `datetime`, `sqlite3`, `threading`, `atexit`

### 7.2 配置检查项
| 检查项 | 状态 | 建议 |
|:---|:---|:---|
| config/.env 权限 | ✅ 600 | 保持 |
| services/*/config/.env 权限 | ❌ 644 | 改为 600 |
| logrotate 配置 | ✅ 已配置 | 保持 |
| TimescaleDB 压缩 | ✅ 30天 | 保持 |
| TimescaleDB 删除 | ✅ 未启用 | 保持 |

### 7.3 网络策略
- 代理探测仅外呼 `api.binance.com`
- 无 SSRF 风险（目标固定）

---

## 8. 需要补充的信息清单

### P0（阻塞高危确认）
- ✅ 已确认：.env 解析逻辑安全
- ✅ 已确认：权限检查硬失败

### P1（量化风险）
- 生产环境配置是否与开发一致
- 实际运行日志样本

### P2（长期治理）
- 安全基线文档
- SDL 流程定义

---

## 9. 行动项（Action Items）

### 立即行动（24 小时内）
| 项目 | 负责人 | 产出物 | 验收标准 |
|:---|:---|:---|:---|
| 修复服务级 .env 权限 | 运维 | 执行 chmod 600 | stat 显示 600 |

**执行命令**:
```bash
chmod 600 services/*/config/.env
```

### 短期修复（1-2 周）
| 项目 | 负责人 | 产出物 | 验收标准 |
|:---|:---|:---|:---|
| 更新 init.sh 设置权限 | 开发 | 脚本修改 | 新建 .env 自动 600 |
| 添加启动脚本测试 | 开发 | 测试用例 | CI 通过 |

### 中长期治理（1-2 月）
| 项目 | 负责人 | 产出物 | 验收标准 |
|:---|:---|:---|:---|
| 安全基线文档 | 安全 | 文档 | 团队评审通过 |
| 密钥管理方案 | 运维 | KMS 集成 | 敏感配置不落盘 |

---

## 10. 审计结论

**总体评估**: 本次安全/稳定性优化变更**有效降低了系统风险**，主要安全问题已修复：

1. ✅ .env 命令注入风险已消除
2. ✅ 权限检查已强制执行
3. ✅ 时间戳比较已统一
4. ✅ 连接池已正确管理
5. ⚠️ 服务级 .env 权限需立即修复

**建议**: 执行上述立即行动项后，可安全推送到生产环境。
