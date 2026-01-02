# TODO 列表（按难度从低到高）

- [x] 日志轮转与压缩（S）✅
  - 添加 `config/logrotate.conf`，按天轮转、保留 14 天并 gzip

- [x] 安全加载 .env + 权限检查（S）✅
  - 三个 `services/*/scripts/start.sh` 用只读键值解析替代 `source .env`
  - 拒绝含 `export`/`$()`/反引号的危险行
  - 检查 `config/.env` 权限，非 600 则警告

- [x] SYMBOLS_* 正则校验（S）✅
  - data-service/trading-service 启动时校验 `^[A-Z0-9]+USDT$`
  - 不符合直接退出

- [x] 时间戳比较改用 datetime（S）✅
  - `data_provider.py::fetch_metric` 使用 `datetime.fromisoformat` 解析
  - 支持 Z/+00:00/无时区等多种格式

- [x] 代理自检与切换（M）✅
  - 启动时 `curl --max-time 3` 测试代理
  - 失败则清空 `HTTP_PROXY/HTTPS_PROXY`

- [x] SQLite 连接复用（M）✅
  - 实现 `_SQLitePool` 连接池（3连接，`check_same_thread=False`）
  - 连接失效自动重建，池满则关闭多余连接
  - 所有查询方法改用 `_get_conn()` / `_return_conn()`

- [x] IO/CPU 拆分执行器（M）✅
  - 新增配置: `MAX_IO_WORKERS`(8) / `MAX_CPU_WORKERS`(4)
  - `COMPUTE_BACKEND` 支持 thread/process/hybrid 三种模式
  - hybrid 模式: 小批量(<50)用线程，大批量用进程

- [ ] 批量拉 K 线/批量算指标（M-L）
  - 抓取：同周期多币种批次请求（如 20/批）或用交易所批量端点；写 TimescaleDB 用多值 insert/COPY。
  - 计算：同周期多 symbol 拼成 DataFrame/ndarray 向量化计算，再拆写结果；单币兜底保留，监控批量失败率。
  - 验证：对比前后吞吐/带宽/CPU 占用，回归数据一致性。

- [ ] TimescaleDB 压缩策略（M-L）
  - 启用压缩：`ALTER TABLE ... SET (timescaledb.compress)`；创建 policy：热数据 30 天不压缩，30 天后自动压缩；可选 180 天自动删除/退役。
  - 验证：`timescaledb_information.compressed_chunk_stats` 查看压缩率；常用窗口查询无显著变慢。
