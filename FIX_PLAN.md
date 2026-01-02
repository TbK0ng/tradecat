# TradeCat 项目修复方案

> 生成时间: 2025-01-03
> 版本: v1.0
> 状态: 待执行

---

## 📋 目录

- [P0 - 高优先级问题](#p0---高优先级问题)
- [P1 - 中优先级问题](#p1---中优先级问题)
- [P2 - 低优先级优化](#p2---低优先级优化)
- [架构重构建议](#架构重构建议)
- [执行计划](#执行计划)

---

## P0 - 高优先级问题

### 问题 1: 硬编码数据库路径

**问题 ID**: P0-001
**严重程度**: 🔴 高
**影响范围**: 部署/迁移
**修复难度**: 低

#### 问题描述

`services/trading-service/config/.env.example` 中硬编码了绝对路径，导致项目迁移或部署时必须手动修改。

```python
# 当前配置
INDICATOR_SQLITE_PATH=/home/lenovo/.projects/tradecat/libs/database/services/telegram-service/market_data.db
```

#### 修复方案

**步骤 1**: 修改 `services/trading-service/config/.env.example`

```diff
- INDICATOR_SQLITE_PATH=/home/lenovo/.projects/tradecat/libs/database/services/telegram-service/market_data.db
+ INDICATOR_SQLITE_PATH=${PROJECT_ROOT}/libs/database/services/telegram-service/market_data.db
```

**步骤 2**: 修改 `services/trading-service/src/simple_scheduler.py`

```python
# 第 29 行附近
PROJECT_ROOT = os.path.dirname(os.path.dirname(TRADING_SERVICE_DIR))
SQLITE_PATH = os.environ.get(
    "INDICATOR_SQLITE_PATH",
    os.path.join(PROJECT_ROOT, "libs/database/services/telegram-service/market_data.db")
).replace("${PROJECT_ROOT}", PROJECT_ROOT)
```

---

## 执行计划

### 阶段一: 高优先级修复 (1-2 周)

| 任务 | 负责人 | 工期 | 依赖 |
|:---|:---:|:---:|:---|
| P0-001: 硬编码路径修复 | Dev | 0.5 天 | - |
| P0-002: 依赖版本锁定 | Dev | 1 天 | - |
| P0-003: 环境变量统一 | Dev | 0.5 天 | - |
| P0-004: 数据库索引优化 | DBA | 2 天 | - |
| P0-005: SQLite 并发优化 | Dev | 2 天 | P0-001 |

---

**文档版本**: v1.0
**最后更新**: 2025-01-03
