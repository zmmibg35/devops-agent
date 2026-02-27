"""
DevOps Agent MCP Server 入口

基于 FastMCP 构建，集成 GitHub + Slack + 禅道，供 Antigravity 调用。
Token 等敏感配置通过环境变量传入，支持团队每人独立配置。
"""

import argparse
import os
import sys
from pathlib import Path

import yaml
from loguru import logger
from mcp.server.fastmcp import FastMCP

from clients.github_client import GitHubClient
from clients.slack_client import SlackClient
from clients.zentao_client import ZentaoClient
from tools.github_tools import register_github_tools
from tools.slack_tools import register_slack_tools
from tools.zentao_tools import register_zentao_tools

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")


def load_config() -> dict:
    """
    加载配置（环境变量优先，config.yaml 作为 fallback）

    优先级: 环境变量 > config.yaml
    """
    # 读取 config.yaml（如果存在）
    config_path = Path(__file__).parent / "config.yaml"
    file_config = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}

    github_file = file_config.get("github", {})
    slack_file = file_config.get("slack", {})
    zentao_file = file_config.get("zentao", {})

    # 环境变量优先
    config = {
        "github": {
            "token": os.environ.get("GITHUB_TOKEN", github_file.get("token", "")),
            "owner": os.environ.get("GITHUB_OWNER", github_file.get("owner", "")),
        },
        "slack": {
            "bot_token": os.environ.get("SLACK_BOT_TOKEN", slack_file.get("bot_token", "")),
            "default_channel": os.environ.get("SLACK_DEFAULT_CHANNEL", slack_file.get("default_channel", "#general")),
        },
        "zentao": {
            "url": os.environ.get("ZENTAO_URL", zentao_file.get("url", "")),
            "account": os.environ.get("ZENTAO_ACCOUNT", zentao_file.get("account", "")),
            "password": os.environ.get("ZENTAO_PASSWORD", zentao_file.get("password", "")),
        },
    }

    # 校验必填项
    if not config["github"]["token"]:
        raise ValueError("缺少 GitHub Token！请设置环境变量 GITHUB_TOKEN 或在 config.yaml 中配置")
    if not config["slack"]["bot_token"]:
        raise ValueError("缺少 Slack Bot Token！请设置环境变量 SLACK_BOT_TOKEN 或在 config.yaml 中配置")

    return config


def main():
    """MCP Server 启动入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="DevOps Agent MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="传输模式：stdio（本地调用）或 sse（远程部署），默认 stdio",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="SSE 模式监听地址，默认 0.0.0.0",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="SSE 模式监听端口，默认 8000",
    )
    args = parser.parse_args()

    config = load_config()
    github_config = config["github"]
    slack_config = config["slack"]

    # 初始化客户端
    github_client = GitHubClient(
        token=github_config["token"],
        owner=github_config.get("owner", ""),
    )
    slack_client = SlackClient(
        bot_token=slack_config["bot_token"],
        default_channel=slack_config.get("default_channel", "#general"),
    )

    # 禅道客户端（可选，配置了才初始化）
    zentao_config = config["zentao"]
    zentao_client = None
    if zentao_config["url"] and zentao_config["account"]:
        zentao_client = ZentaoClient(
            url=zentao_config["url"],
            account=zentao_config["account"],
            password=zentao_config["password"],
        )

    # 构建快捷指令提示词
    shortcuts = (
        "\n\n"
        "## 快捷指令（自然语言 → 自动化操作）\n"
        "当用户使用以下自然语言表达时，自动执行对应的组合操作：\n"
        "\n"
        "### 1. 创建需求 / 提需求\n"
        "触发词：「创建需求」「提需求」「新需求」「需求给XX」\n"
        "操作：\n"
        "  ① GitHub 创建 Issue（标签: enhancement，指派给对应人）\n"
        "  ② Slack 发送通知（包含需求标题、负责人、GitHub 链接）\n"
        "\n"
        "### 2. 提 Bug / 报 Bug\n"
        "触发词：「提Bug」「报Bug」「有个Bug」「发现Bug」\n"
        "操作：\n"
        "  ① GitHub 创建 Issue（标签: bug，指派给对应人）\n"
        "  ② Slack 发送通知（包含 Bug 描述和 GitHub 链接）\n"
        "  ③ 如果禅道已集成，同步在禅道创建 Bug\n"
        "\n"
        "### 3. 创建任务 / 派任务\n"
        "触发词：「创建任务」「派任务」「安排任务」「任务给XX」\n"
        "操作：\n"
        "  ① Slack 创建任务卡片（含负责人 @提及、优先级）\n"
        "  ② GitHub 创建 Issue（标签: task）\n"
        "\n"
        "### 4. 查看进度 / 项目状态\n"
        "触发词：「查看进度」「项目状态」「最近提交」「今天做了什么」\n"
        "操作：\n"
        "  ① 查询 GitHub 最近的提交记录\n"
        "  ② 查询未关闭的 Issue 和 PR 列表\n"
        "  ③ 汇总后发送到 Slack\n"
        "\n"
        "### 5. 发布通知 / 通知团队\n"
        "触发词：「通知团队」「发布通知」「告诉大家」「广播」\n"
        "操作：\n"
        "  ① 将消息发送到 Slack 默认频道\n"
        "\n"
        "### 6. 代码审查 / 查看变更\n"
        "触发词：「查看代码」「代码审查」「看看改了什么」「最近的变更」\n"
        "操作：\n"
        "  ① 获取最近的提交记录\n"
        "  ② 查看提交的 Diff 详情\n"
        "\n"
        "## 通用规则\n"
        "- 当提到人名时，尝试匹配 GitHub 用户名进行指派\n"
        "- 涉及通知时，默认同步发送 Slack 消息\n"
        "- 如果用户未指定仓库，使用默认仓库\n"
        "- 如果用户未指定优先级，默认使用「普通」\n"
        "- Slack 通知应包含操作摘要和相关链接\n"
    )

    # 创建 MCP Server
    mcp = FastMCP(
        "DevOps Agent",
        instructions=(
            "DevOps Agent：集成 GitHub、Slack 和禅道的 DevOps 工具。\n"
            "可以查询 GitHub 的提交记录、PR、Issue、代码文件，\n"
            "发送消息到 Slack、创建和更新任务，\n"
            "以及管理禅道的 Bug、任务、需求。\n"
            f"GitHub 默认用户: {github_config.get('owner', '')}"
            + shortcuts
        ),
    )

    # 注册所有 Tools
    register_github_tools(mcp, github_client)
    register_slack_tools(mcp, slack_client)
    if zentao_client:
        register_zentao_tools(mcp, zentao_client)
        logger.info(f"禅道已集成: {zentao_config['url']}")

    logger.info("DevOps Agent MCP Server 启动中...")
    logger.info(f"传输模式: {args.transport}")
    logger.info(f"GitHub owner: {github_config.get('owner', '')}")
    logger.info(f"Slack 默认频道: {slack_config.get('default_channel', '#general')}")

    if args.transport == "sse":
        logger.info(f"SSE 监听地址: {args.host}:{args.port}")

    # 启动服务
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
