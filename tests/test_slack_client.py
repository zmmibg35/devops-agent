"""
Slack Client 单元测试
"""

from clients.slack_client import SlackClient


class TestBuildTaskBlocks:
    """测试任务卡片构建（纯函数，无需 Mock）"""

    def test_basic_task_blocks(self):
        """基础任务卡片"""
        blocks = SlackClient.build_task_blocks(title="测试任务")
        assert len(blocks) >= 3
        # 第一个是 header
        assert blocks[0]["type"] == "header"
        assert "测试任务" in blocks[0]["text"]["text"]

    def test_task_blocks_with_description(self):
        """带描述的任务卡片"""
        blocks = SlackClient.build_task_blocks(
            title="测试任务",
            description="这是一个测试描述",
        )
        # 应包含描述 section
        desc_blocks = [b for b in blocks if b.get("type") == "section" and "描述" in str(b)]
        assert len(desc_blocks) == 1

    def test_task_blocks_with_assignee(self):
        """带负责人的任务卡片"""
        blocks = SlackClient.build_task_blocks(
            title="测试任务",
            assignee="<@U123456>",
        )
        # fields 中应包含负责人
        section_blocks = [b for b in blocks if b.get("type") == "section" and "fields" in b]
        assert len(section_blocks) == 1
        fields_text = str(section_blocks[0]["fields"])
        assert "负责人" in fields_text

    def test_task_blocks_priority(self):
        """自定义优先级"""
        blocks = SlackClient.build_task_blocks(
            title="紧急任务",
            priority="紧急",
        )
        section_blocks = [b for b in blocks if b.get("type") == "section" and "fields" in b]
        fields_text = str(section_blocks[0]["fields"])
        assert "紧急" in fields_text

    def test_task_blocks_has_context(self):
        """末尾有 context 标识"""
        blocks = SlackClient.build_task_blocks(title="测试")
        last_block = blocks[-1]
        assert last_block["type"] == "context"
        assert "DevOps Agent" in str(last_block)
