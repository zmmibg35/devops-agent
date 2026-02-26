"""
DevOps Agent MCP Server 入口

基于 FastMCP 构建，集成 GitHub + Slack，供 Antigravity 调用。
Token 等敏感配置通过环境变量传入，支持团队每人独立配置。
"""

import os
import sys
from pathlib import Path

import yaml
from loguru import logger
from mcp.server.fastmcp import FastMCP

from clients.github_client import GitHubClient
from clients.slack_client import SlackClient
from tools.github_tools import register_github_tools
from tools.slack_tools import register_slack_tools

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
        with open(config_path, "r", encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}

    github_file = file_config.get("github", {})
    slack_file = file_config.get("slack", {})

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
    }

    # 校验必填项
    if not config["github"]["token"]:
        raise ValueError("缺少 GitHub Token！请设置环境变量 GITHUB_TOKEN 或在 config.yaml 中配置")
    if not config["slack"]["bot_token"]:
        raise ValueError("缺少 Slack Bot Token！请设置环境变量 SLACK_BOT_TOKEN 或在 config.yaml 中配置")

    return config


def main():
    """MCP Server 启动入口"""
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

    # 创建 MCP Server
    mcp = FastMCP(
        "DevOps Agent",
        instructions=(
            "DevOps Agent：集成 GitHub 和 Slack 的 DevOps 工具。\n"
            "可以查询 GitHub 的提交记录、PR、Issue、代码文件，\n"
            "也可以发送消息到 Slack、创建和更新任务。\n"
            f"GitHub 默认用户: {github_config.get('owner', '')}"
        ),
    )

    # 注册所有 Tools
    register_github_tools(mcp, github_client)
    register_slack_tools(mcp, slack_client)

    logger.info("DevOps Agent MCP Server 启动中...")
    logger.info(f"GitHub owner: {github_config.get('owner', '')}")
    logger.info(f"Slack 默认频道: {slack_config.get('default_channel', '#general')}")

    mcp.run()


if __name__ == "__main__":
    main()
