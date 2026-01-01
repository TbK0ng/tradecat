# Telegram Service

加密市场情报 Telegram 机器人，提供排行榜卡片、单币快照、信号订阅等功能。

## 功能

- **44 张排行榜卡片** - 基础/合约/高级三类，支持多周期切换
- **单币快照** - 输入 `btc!` 查看单币种多维度数据
- **信号订阅** - 用户可订阅指标信号推送
- **AI 分析** - 集成 AI 的非阻塞分析（可选）

## 目录结构

```
src/
├── bot/
│   ├── app.py                  # 主入口，路由，状态管理
│   ├── single_token_snapshot.py # 单币快照渲染
│   ├── signal_formatter.py     # 信号文案格式化
│   └── non_blocking_ai_handler.py # 异步 AI 处理
├── cards/
│   ├── basic/                  # 基础指标卡片 (10张)
│   ├── futures/                # 合约指标卡片 (20张)
│   ├── advanced/               # 高级指标卡片 (10张)
│   ├── data_provider.py        # SQLite 数据读取
│   └── registry.py             # 卡片注册表
├── config/
└── main.py                     # 入口
```

## 快速开始

### 环境要求

- Python >= 3.10
- SQLite (market_data.db)

### 安装

```bash
pip install python-telegram-bot httpx aiohttp
```

### 配置

复制 `.env.example` 为 `.env`：

```bash
# 必填
TELEGRAM_BOT_TOKEN=your_bot_token_here

# 可选
DATABASE_URL=postgresql://user:pass@localhost:5432/market_data
HTTP_PROXY=http://127.0.0.1:7890
BINANCE_API_DISABLED=1
```

### 启动

```bash
cd services/telegram-service
python -m src.main
```

## 卡片列表

### 基础卡片 (10张)
- KDJ、MACD柱状、OBV、RSI谐波
- 布林带、成交量、成交量比率
- 支撑阻力、资金流向

### 合约卡片 (20张)
- 持仓排行、OI趋势、OI连续性、OI极值告警
- 主动买卖比、主动成交方向、主动跳变、主动连续性
- 大户情绪、全市场情绪、情绪分歧、情绪动量
- 持仓增减速、期货持仓情绪、波动度
- 翻转雷达、风险拥挤度、市场深度、资金费率、爆仓

### 高级卡片 (10张)
- ATR、CVD、EMA、K线形态、MFI
- VPVR、VWAP、流动性、超级精准趋势、趋势线

## 数据流

```
market_data.db (SQLite)
        │
        ▼
    data_provider.py (读取)
        │
        ▼
    cards/*.py (渲染)
        │
        ▼
    Telegram Bot (发送)
```

## 常见问题

### Bot 启动冲突

```
telegram.error.Conflict: Terminated by other getUpdates request
```

确保只有一个 Bot 实例在运行。

### 数据读取为空

1. 检查 `data/market_data.db` 是否存在
2. 确认 trading-service 已运行并写入数据
3. 查看日志中的 SQLite 查询错误
