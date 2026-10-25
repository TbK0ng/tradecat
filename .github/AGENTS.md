# 统一目录归属

继续遵守根目录 AGENTS.md 和各子目录的安全、来源只读及 paper/watch 约束。

- 仓库根目录只允许 `.git/`、`.github/` 两个目录；根目录文件不迁移，不创建旧路径或兼容链接。
- 源码、测试、契约、Skill、脚本、文档与容器配置均在本目录，机器契约中的路径仍以仓库根为基准，使用 `.github/` 前缀。
- 工作流仍固定在 `.github/workflows/`，不嵌套第二层 .github/workflows。
- `.runtime/`、`.hermes/`、`.tools/`、`.venv/` 和缓存必须保持 ignored，绝不提交账本、日志、环境或凭据。
- 原始上游参考快照保持只读；目录迁移不改变其内容、hash 或 public-readonly 安全边界。
- Python 项目元数据保留在根目录 pyproject.toml；从仓库根执行命令，开发环境位于 `.github/.venv/`。
- 本轮不执行真实交易，不连接私有账户，不启动常驻 loop，不删除现有运行数据，不提交或推送。
