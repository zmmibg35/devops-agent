# DevOps Agent

> AI 驱动的 DevOps 智能助手 —— 基于 MCP 协议，集成 GitHub、Slack 和禅道。

通过自然语言与 AI 对话，即可完成日常 DevOps 操作：创建需求、提 Bug、查看进度、通知团队……

## ✨ 功能概览

### 🔗 GitHub 集成
| 功能 | 说明 |
|------|------|
| 仓库管理 | 搜索和查看仓库列表 |
| 提交记录 | 按分支、时间范围查询提交，查看 Diff |
| PR 管理 | 获取 Pull Request 列表 |
| Issue 管理 | 创建、更新、查询 Issue |
| Actions | 查看 CI/CD 工作流运行记录 |
| Projects | 列出看板、将 Issue 添加到看板 |
| 代码搜索 | 在仓库中搜索代码 |

### 💬 Slack 集成
| 功能 | 说明 |
|------|------|
| 消息发送 | 发送消息到指定频道（支持 mrkdwn） |
| 任务卡片 | 创建任务卡片（含 @提及通知） |
| 任务更新 | 更新任务状态（待处理 → 进行中 → 已完成） |
| 频道管理 | 获取工作区频道列表 |

### 📋 禅道集成（可选）
| 功能 | 说明 |
|------|------|
| 产品 & 项目 | 获取产品和项目列表 |
| Bug 管理 | 创建、查询、查看 Bug 详情 |
| 任务管理 | 创建和查询任务 |
| 需求管理 | 查询需求列表 |

### 🚀 快捷指令
通过自然语言触发多平台联动操作：

| 说的话 | AI 自动做 |
|--------|----------|
| "创建需求给XX" | GitHub Issue + Slack 通知 |
| "提个 Bug" | GitHub Issue + Slack 通知 + 禅道 Bug |
| "派任务给XX" | Slack 任务卡片 + GitHub Issue |
| "查看进度" | 查 commits + Issues → Slack 汇总 |
| "通知团队" | Slack 消息广播 |

## 🏗️ 项目结构

```
devops-agent/
├── server.py              # MCP Server 入口
├── config.yaml            # 配置文件（gitignored）
├── pyproject.toml         # 项目元数据和依赖
├── clients/               # API 客户端层
│   ├── github_client.py   # GitHub REST + GraphQL 客户端
│   ├── slack_client.py    # Slack Web API 客户端
│   └── zentao_client.py   # 禅道 REST API 客户端
├── tools/                 # MCP 工具注册层
│   ├── github_tools.py    # GitHub 工具（12 项）
│   ├── slack_tools.py     # Slack 工具（4 项）
│   └── zentao_tools.py    # 禅道工具（9 项）
└── tests/                 # 测试
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 2. 安装依赖

```bash
uv sync
```

### 3. 配置

复制配置模板并填入实际值：

```bash
cp .env.example .env
```

需要配置的项目：

| 变量 | 说明 | 必填 |
|------|------|:----:|
| `GITHUB_TOKEN` | GitHub Personal Access Token | ✅ |
| `GITHUB_OWNER` | GitHub 用户名/组织名 | ✅ |
| `SLACK_BOT_TOKEN` | Slack Bot User OAuth Token | ✅ |
| `SLACK_DEFAULT_CHANNEL` | Slack 默认频道 | ❌ |
| `ZENTAO_URL` | 禅道访问地址 | ❌ |
| `ZENTAO_ACCOUNT` | 禅道账号 | ❌ |
| `ZENTAO_PASSWORD` | 禅道密码 | ❌ |

### 4. 启动

**本地模式（stdio）：**
```bash
uv run python server.py
```

**远程模式（SSE）：**
```bash
uv run python server.py --transport sse --port 8000
```

### 5. 接入 AI 客户端

在 Antigravity MCP 配置中添加：

```json
{
  "mcpServers": {
    "devops-agent": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/devops-agent", "python", "server.py"]
    }
  }
}
```

## 🛠️ 开发指南

### 添加新工具

1. 在 `clients/` 中添加 API 客户端方法
2. 在 `tools/` 中注册 MCP 工具
3. 在 `server.py` 中初始化客户端并注册工具

### 运行测试

```bash
uv run pytest tests/ -v
```

## 📄 License

MIT
