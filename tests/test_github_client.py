"""
GitHub Client 单元测试
"""

from unittest.mock import AsyncMock, patch

import pytest

from clients.github_client import GitHubClient


@pytest.fixture
def client():
    """创建测试用 GitHub 客户端"""
    return GitHubClient(token="test-token", owner="test-owner")


class TestFullRepo:
    """测试仓库名补全逻辑"""

    def test_short_name_with_owner(self, client):
        """短名自动拼接 owner"""
        assert client._full_repo("my-repo") == "test-owner/my-repo"

    def test_full_name_unchanged(self, client):
        """完整名称不变"""
        assert client._full_repo("other/repo") == "other/repo"

    def test_short_name_no_owner(self):
        """无默认 owner 时直接返回短名"""
        c = GitHubClient(token="test-token", owner="")
        assert c._full_repo("my-repo") == "my-repo"


class TestGetCommits:
    """测试获取提交记录"""

    @pytest.mark.asyncio
    async def test_get_commits_basic(self, client):
        """基础获取提交记录"""
        mock_response = [
            {"sha": "abc123", "commit": {"message": "初始提交"}},
            {"sha": "def456", "commit": {"message": "添加功能"}},
        ]
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await client.get_commits("my-repo")
            assert len(result) == 2
            assert result[0]["sha"] == "abc123"

    @pytest.mark.asyncio
    async def test_get_commits_with_branch(self, client):
        """指定分支获取提交"""
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=[]) as mock_req:
            await client.get_commits("my-repo", branch="dev")
            call_args = mock_req.call_args
            assert call_args[0][1] == "/repos/test-owner/my-repo/commits"
            assert call_args[0][2]["sha"] == "dev"


class TestGetIssues:
    """测试 Issue 查询"""

    @pytest.mark.asyncio
    async def test_filters_pull_requests(self, client):
        """验证 PR 被过滤掉"""
        mock_response = [
            {"number": 1, "title": "真正的 Issue"},
            {"number": 2, "title": "这是 PR", "pull_request": {"url": "..."}},
        ]
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await client.get_issues("my-repo")
            assert len(result) == 1
            assert result[0]["title"] == "真正的 Issue"


class TestCreateIssue:
    """测试创建 Issue"""

    @pytest.mark.asyncio
    async def test_create_issue_basic(self, client):
        """基础创建 Issue"""
        mock_response = {"number": 10, "title": "测试 Issue", "state": "open"}
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            result = await client.create_issue("my-repo", title="测试 Issue")
            assert result["number"] == 10
            call_args = mock_req.call_args
            assert call_args[1]["json_body"]["title"] == "测试 Issue"

    @pytest.mark.asyncio
    async def test_create_issue_with_labels(self, client):
        """创建带标签的 Issue"""
        mock_response = {"number": 11, "title": "Bug", "state": "open"}
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            await client.create_issue("my-repo", title="Bug", labels=["bug", "urgent"])
            call_args = mock_req.call_args
            assert call_args[1]["json_body"]["labels"] == ["bug", "urgent"]
