# Changelog

## [0.2.0] - 2026-02-27

### 新增
- 📖 添加 `README.md` 项目文档
- 🧪 添加单元测试框架（pytest + pytest-asyncio），覆盖 GitHub/Slack/Server 模块
- 🔧 添加 GitHub Actions CI 工作流（lint + test）
- 🚨 添加自定义异常体系（`clients/exceptions.py`）
- 🚀 添加快捷指令提示词（创建需求、提 Bug、派任务等自然语言联动）
- 📋 添加 `CHANGELOG.md`

### 修复
- 🐛 修复 `pyproject.toml` 描述（GitLab → GitHub）
- 🐛 修复 `.gitignore` 错误排除测试文件
- 🐛 修复 `github_client.py` 每次请求创建新 HTTP Client 的问题

### 改进
- ♻️ 统一日志级别规范（查询用 debug，写入用 info）
- ♻️ 配置 ruff 代码检查工具
- ♻️ `github_client.py` 异常处理改用自定义 `GitHubAPIError`

## [0.1.0] - 2026-02-26

### 新增
- 🔗 GitHub 集成（仓库、提交、PR、Issue、Actions、Projects V2）
- 💬 Slack 集成（消息、任务卡片、频道管理）
- 📋 禅道集成（产品、项目、Bug、任务、需求）
- ⚡ MCP Server 入口（stdio + SSE 双模式）
