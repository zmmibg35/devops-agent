"""
Slack Web API 客户端

封装 Slack API 的消息发送、任务管理等操作。
"""

from typing import Optional

from loguru import logger
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
    """Slack Web API 异步客户端"""

    def __init__(self, bot_token: str, default_channel: str = "#general"):
        """
        初始化 Slack 客户端

        Args:
            bot_token: Bot User OAuth Token（xoxb- 开头）
            default_channel: 默认频道
        """
        self.client = AsyncWebClient(token=bot_token)
        self.default_channel = default_channel
        # 用户名缓存：避免重复调用 API
        self._user_cache: dict[str, dict] = {}
        # 频道缓存：避免重复调用 API
        self._channel_cache: dict[str, dict] = {}

    async def send_message(
        self,
        text: str,
        channel: Optional[str] = None,
    ) -> dict:
        """发送文本消息"""
        ch = channel or self.default_channel
        try:
            response = await self.client.chat_postMessage(channel=ch, text=text)
            logger.info(f"消息已发送到 {ch}")
            return {
                "ok": response["ok"],
                "channel": response["channel"],
                "ts": response["ts"],
            }
        except SlackApiError as e:
            logger.error(f"发送消息失败: {e.response['error']}")
            raise

    async def send_blocks(
        self,
        blocks: list[dict],
        text: str = "",
        channel: Optional[str] = None,
    ) -> dict:
        """发送 Block Kit 富文本消息"""
        ch = channel or self.default_channel
        try:
            response = await self.client.chat_postMessage(
                channel=ch, blocks=blocks, text=text
            )
            logger.info(f"Block 消息已发送到 {ch}")
            return {
                "ok": response["ok"],
                "channel": response["channel"],
                "ts": response["ts"],
            }
        except SlackApiError as e:
            logger.error(f"发送 Block 消息失败: {e.response['error']}")
            raise

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str = "",
        blocks: Optional[list[dict]] = None,
    ) -> dict:
        """更新已发送的消息（用于更新任务状态）"""
        try:
            kwargs = {"channel": channel, "ts": ts, "text": text}
            if blocks:
                kwargs["blocks"] = blocks
            response = await self.client.chat_update(**kwargs)
            logger.info(f"消息已更新: channel={channel}, ts={ts}")
            return {
                "ok": response["ok"],
                "channel": response["channel"],
                "ts": response["ts"],
            }
        except SlackApiError as e:
            logger.error(f"更新消息失败: {e.response['error']}")
            raise

    async def list_channels(self, limit: int = 100) -> list[dict]:
        """获取频道列表"""
        try:
            response = await self.client.conversations_list(
                types="public_channel,private_channel", limit=limit
            )
            channels = response.get("channels", [])
            logger.debug(f"获取到 {len(channels)} 个频道")
            return [
                {"id": ch["id"], "name": ch["name"]}
                for ch in channels
            ]
        except SlackApiError as e:
            logger.error(f"获取频道列表失败: {e.response['error']}")
            raise

    # ==================== 频道解析 ====================

    async def _load_all_channels(self) -> None:
        """加载所有公共频道到缓存"""
        if self._channel_cache:
            return
        try:
            cursor = None
            while True:
                kwargs: dict = {"types": "public_channel,private_channel", "limit": 200}
                if cursor:
                    kwargs["cursor"] = cursor
                response = await self.client.conversations_list(**kwargs)
                for ch in response.get("channels", []):
                    self._channel_cache[ch["id"]] = {
                        "id": ch["id"],
                        "name": ch["name"],
                    }
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
            logger.info(f"已加载 {len(self._channel_cache)} 个频道到缓存")
        except SlackApiError as e:
            logger.error(f"加载频道列表失败: {e.response['error']}")
            raise

    async def resolve_channel(self, name: str) -> Optional[dict]:
        """
        通过频道名称解析为频道信息

        支持带/不带 '#' 前缀（如 '#general' 或 'general'）。
        先精确匹配，后模糊匹配。

        Args:
            name: 频道名称

        Returns:
            匹配到的频道信息（含 id、name），未找到返回 None
        """
        await self._load_all_channels()
        # 去掉 '#' 前缀并统一小写
        name_clean = name.lstrip("#").lower().strip()
        if not name_clean:
            return None

        # 精确匹配
        for ch in self._channel_cache.values():
            if ch["name"].lower() == name_clean:
                logger.info(f"精确匹配频道: {name} → #{ch['name']} (ID: {ch['id']})")
                return ch

        # 模糊匹配（频道名包含输入关键词）
        for ch in self._channel_cache.values():
            if name_clean in ch["name"].lower():
                logger.info(f"模糊匹配频道: {name} → #{ch['name']} (ID: {ch['id']})")
                return ch

        logger.warning(f"未找到频道: {name}")
        return None

    async def validate_and_resolve_channel(self, name: str) -> tuple[Optional[str], Optional[str]]:
        """
        校验并解析频道名称，返回 (频道ID, 错误信息)

        成功时返回 (channel_id, None)，失败时返回 (None, 错误描述)

        Args:
            name: 频道名称

        Returns:
            (channel_id, error_message) 二元组
        """
        ch = await self.resolve_channel(name)
        if ch:
            return ch["id"], None

        # 构建友好错误信息，列出可用频道
        await self._load_all_channels()
        available = [f"#{c['name']}" for c in self._channel_cache.values()]
        available_str = "、".join(available) if available else "无"
        error_msg = (
            f"频道 '{name}' 不存在或 Bot 未加入该频道。\n"
            f"当前可用频道: {available_str}"
        )
        return None, error_msg

    # ==================== 用户查找 ====================

    async def _load_all_users(self) -> None:
        """加载所有用户到缓存"""
        if self._user_cache:
            return
        try:
            cursor = None
            while True:
                kwargs = {"limit": 200}
                if cursor:
                    kwargs["cursor"] = cursor
                response = await self.client.users_list(**kwargs)
                for user in response.get("members", []):
                    if user.get("deleted") or user.get("is_bot"):
                        continue
                    self._user_cache[user["id"]] = {
                        "id": user["id"],
                        "name": user.get("name", ""),
                        "real_name": user.get("real_name", ""),
                        "display_name": user.get("profile", {}).get("display_name", ""),
                    }
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
            logger.info(f"已加载 {len(self._user_cache)} 个用户到缓存")
        except SlackApiError as e:
            logger.error(f"加载用户列表失败: {e.response['error']}")
            raise

    async def find_user_by_name(self, name: str) -> Optional[dict]:
        """
        通过名字查找 Slack 用户（支持中文名、英文名、用户名模糊匹配）

        Args:
            name: 用户名字（如 "王志明"、"zhiming"、"wangzm"）

        Returns:
            匹配到的用户信息（含 id），未找到返回 None
        """
        await self._load_all_users()
        name_lower = name.lower().strip()
        # 精确匹配优先
        for user in self._user_cache.values():
            if name_lower in (
                user["real_name"].lower(),
                user["display_name"].lower(),
                user["name"].lower(),
            ):
                logger.info(f"精确匹配用户: {name} → {user['real_name']} (ID: {user['id']})")
                return user
        # 模糊匹配
        for user in self._user_cache.values():
            if (
                name_lower in user["real_name"].lower()
                or name_lower in user["display_name"].lower()
                or name_lower in user["name"].lower()
            ):
                logger.info(f"模糊匹配用户: {name} → {user['real_name']} (ID: {user['id']})")
                return user
        logger.warning(f"未找到用户: {name}")
        return None

    async def list_workspace_members(self) -> list[dict]:
        """获取工作区所有成员列表"""
        await self._load_all_users()
        return list(self._user_cache.values())

    # ==================== 任务卡片构建 ====================

    @staticmethod
    def build_task_blocks(
        title: str,
        description: str = "",
        assignee: str = "",
        status: str = "📋 待处理",
        priority: str = "普通",
    ) -> list[dict]:
        """
        构建任务卡片的 Block Kit 组件

        Args:
            title: 任务标题
            description: 任务描述
            assignee: 负责人（支持 <@U123> 格式来 @提及）
            status: 任务状态
            priority: 优先级
        """
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📌 {title}", "emoji": True},
            },
            {"type": "divider"},
        ]

        # 任务详情字段
        fields = [
            {"type": "mrkdwn", "text": f"*状态:*\n{status}"},
            {"type": "mrkdwn", "text": f"*优先级:*\n{priority}"},
        ]
        if assignee:
            fields.append({"type": "mrkdwn", "text": f"*负责人:*\n{assignee}"})
        blocks.append({"type": "section", "fields": fields})

        # 描述部分
        if description:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*描述:*\n{description}"},
            })

        # 时间戳
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "创建自 DevOps Agent | Antigravity MCP"}
            ],
        })

        return blocks
