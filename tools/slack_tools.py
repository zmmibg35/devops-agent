"""
Slack MCP Tools

注册与 Slack 相关的 MCP 工具：消息发送、任务管理、用户查找。
"""

import json

from mcp.server.fastmcp import FastMCP

from clients.slack_client import SlackClient


def register_slack_tools(mcp: FastMCP, client: SlackClient):
    """将 Slack 工具注册到 MCP Server"""

    @mcp.tool()
    async def slack_send_message(
        text: str,
        channel: str = "",
    ) -> str:
        """发送消息到 Slack 频道。

        Args:
            text: 消息内容（支持 Slack mrkdwn 格式，如 *加粗*、`代码`、> 引用）
            channel: 目标频道（如 #general），留空则使用默认频道
        """
        # 指定了频道时，先解析并校验频道名称
        target_channel = None
        if channel:
            channel_id, error = await client.validate_and_resolve_channel(channel)
            if error:
                return json.dumps({"ok": False, "error": error}, ensure_ascii=False, indent=2)
            target_channel = channel_id

        result = await client.send_message(
            text=text,
            channel=target_channel,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def slack_create_task(
        title: str,
        description: str = "",
        assignee: str = "",
        priority: str = "普通",
        channel: str = "",
    ) -> str:
        """在 Slack 频道创建一个需求任务卡片。

        创建后会返回 channel 和 ts（消息 ID），后续可通过 slack_update_task 更新状态。

        Args:
            title: 任务标题
            description: 任务描述
            assignee: 负责人用户名（逗号分隔），留空不限
            priority: 优先级（紧急 / 高 / 普通 / 低）
            channel: 目标频道（如 #general），留空则使用默认频道
        """
        # 指定了频道时，先解析并校验频道名称
        target_channel = None
        if channel:
            channel_id, error = await client.validate_and_resolve_channel(channel)
            if error:
                return json.dumps({"ok": False, "error": error}, ensure_ascii=False, indent=2)
            target_channel = channel_id

        # 如果指定了负责人，尝试通过名字查找 Slack 用户并 @提及
        display_assignee = assignee
        if assignee:
            user = await client.find_user_by_name(assignee)
            if user:
                # 使用 <@用户ID> 格式，Slack 会自动渲染为 @提及并通知对方
                display_assignee = f"<@{user['id']}>"

        blocks = SlackClient.build_task_blocks(
            title=title,
            description=description,
            assignee=display_assignee,
            status="📋 待处理",
            priority=priority,
        )
        result = await client.send_blocks(
            blocks=blocks,
            text=f"📌 新任务: {title}",
            channel=target_channel,
        )
        return json.dumps({
            **result,
            "message": f"任务 '{title}' 已创建。请保存 channel={result['channel']} 和 ts={result['ts']}，用于后续更新任务状态。",
        }, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def slack_update_task(
        channel: str,
        ts: str,
        title: str,
        status: str,
        description: str = "",
        assignee: str = "",
        priority: str = "普通",
    ) -> str:
        """更新 Slack 上已有的任务卡片状态。

        需要提供创建任务时返回的 channel 和 ts。

        Args:
            channel: 任务消息所在的频道 ID
            ts: 任务消息的时间戳 ID（创建任务时返回的 ts 值）
            title: 任务标题
            status: 新的任务状态（如：📋 待处理 / 🔄 进行中 / ✅ 已完成 / ❌ 已取消）
            description: 任务描述
            assignee: 负责人
            priority: 优先级
        """
        # 如果指定了负责人，尝试查找并 @提及
        display_assignee = assignee
        if assignee and not assignee.startswith("<@"):
            user = await client.find_user_by_name(assignee)
            if user:
                display_assignee = f"<@{user['id']}>"

        blocks = SlackClient.build_task_blocks(
            title=title,
            description=description,
            assignee=display_assignee,
            status=status,
            priority=priority,
        )
        result = await client.update_message(
            channel=channel,
            ts=ts,
            text=f"📌 任务更新: {title} - {status}",
            blocks=blocks,
        )
        return json.dumps({
            **result,
            "message": f"任务 '{title}' 状态已更新为: {status}",
        }, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def slack_list_channels() -> str:
        """获取 Slack 工作区的公共频道列表。"""
        channels = await client.list_channels()
        return json.dumps(channels, ensure_ascii=False, indent=2)
