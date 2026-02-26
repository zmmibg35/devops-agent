"""
GitHub MCP Tools

注册与 GitHub 相关的 MCP 工具：提交记录、PR、Issue、代码文件、Actions。
"""

import json

from mcp.server.fastmcp import FastMCP

from clients.github_client import GitHubClient


def register_github_tools(mcp: FastMCP, client: GitHubClient):
    """将 GitHub 工具注册到 MCP Server"""

    # ==================== 仓库 ====================

    @mcp.tool()
    async def github_list_repos(search: str = "") -> str:
        """搜索 GitHub 仓库列表。

        Args:
            search: 搜索关键词，留空则返回自己最近更新的仓库
        """
        if search:
            repos = await client.search_repos(query=search)
        else:
            repos = await client.list_repos()
        result = []
        for r in repos:
            result.append({
                "full_name": r["full_name"],
                "description": r.get("description", "") or "",
                "html_url": r["html_url"],
                "default_branch": r.get("default_branch", "main"),
                "language": r.get("language", ""),
                "updated_at": r.get("updated_at", ""),
                "private": r.get("private", False),
            })
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ==================== 提交记录 ====================

    @mcp.tool()
    async def github_get_commits(
        repo: str,
        branch: str = "",
        since: str = "",
        until: str = "",
        per_page: int = 20,
    ) -> str:
        """获取 GitHub 仓库的代码提交记录。

        Args:
            repo: 仓库名（如 owner/repo 或短名，短名自动拼接默认 owner）
            branch: 分支名，留空使用默认分支
            since: 起始时间（ISO 8601 格式，如 2026-02-26T00:00:00+08:00），留空不限
            until: 截止时间（ISO 8601 格式），留空不限
            per_page: 返回条数，默认 20
        """
        commits = await client.get_commits(
            repo=repo,
            branch=branch,
            since=since or None,
            until=until or None,
            per_page=per_page,
        )
        result = []
        for c in commits:
            commit_data = c.get("commit", {})
            result.append({
                "sha": c["sha"][:8],
                "message": commit_data.get("message", "").strip(),
                "author": commit_data.get("author", {}).get("name", ""),
                "date": commit_data.get("author", {}).get("date", ""),
                "html_url": c.get("html_url", ""),
            })
        return json.dumps(result, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def github_get_commit_diff(
        repo: str,
        sha: str,
    ) -> str:
        """查看某次提交的代码变更（Diff）。

        Args:
            repo: 仓库名（如 owner/repo）
            sha: 提交的 SHA 值
        """
        detail = await client.get_commit_detail(repo=repo, sha=sha)
        files = detail.get("files", [])
        result = []
        for f in files:
            result.append({
                "filename": f.get("filename", ""),
                "status": f.get("status", ""),
                "additions": f.get("additions", 0),
                "deletions": f.get("deletions", 0),
                "patch": f.get("patch", "")[:500],  # 截断过长的 diff
            })
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ==================== Pull Request ====================

    @mcp.tool()
    async def github_get_pull_requests(
        repo: str,
        state: str = "open",
        per_page: int = 20,
    ) -> str:
        """获取 GitHub 仓库的 Pull Request 列表。

        Args:
            repo: 仓库名（如 owner/repo）
            state: 状态筛选：open / closed / all
            per_page: 返回条数，默认 20
        """
        prs = await client.get_pull_requests(repo=repo, state=state, per_page=per_page)
        result = []
        for pr in prs:
            result.append({
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "user": pr.get("user", {}).get("login", ""),
                "head": pr.get("head", {}).get("ref", ""),
                "base": pr.get("base", {}).get("ref", ""),
                "created_at": pr["created_at"],
                "html_url": pr["html_url"],
            })
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ==================== Issue 管理 ====================

    @mcp.tool()
    async def github_get_issues(
        repo: str,
        state: str = "open",
        labels: str = "",
        per_page: int = 20,
    ) -> str:
        """获取 GitHub 仓库的 Issue 列表。

        Args:
            repo: 仓库名（如 owner/repo）
            state: 状态筛选：open / closed / all
            labels: 标签筛选（逗号分隔），留空不限
            per_page: 返回条数，默认 20
        """
        issues = await client.get_issues(
            repo=repo, state=state, labels=labels or None, per_page=per_page,
        )
        result = []
        for issue in issues:
            assignees = [a.get("login", "") for a in issue.get("assignees", [])]
            result.append({
                "number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "user": issue.get("user", {}).get("login", ""),
                "assignees": assignees,
                "labels": [l.get("name", "") for l in issue.get("labels", [])],
                "created_at": issue["created_at"],
                "html_url": issue["html_url"],
            })
        return json.dumps(result, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def github_create_issue(
        repo: str,
        title: str,
        body: str = "",
        labels: str = "",
        assignees: str = "",
    ) -> str:
        """在 GitHub 仓库上创建一个新 Issue。

        Args:
            repo: 仓库名（如 owner/repo）
            title: Issue 标题
            body: Issue 描述（支持 Markdown 格式）
            labels: 标签（逗号分隔，如 "bug,urgent"）
            assignees: 指派人用户名（逗号分隔）
        """
        label_list = [l.strip() for l in labels.split(",") if l.strip()] if labels else None
        assignee_list = [a.strip() for a in assignees.split(",") if a.strip()] if assignees else None
        issue = await client.create_issue(
            repo=repo, title=title, body=body,
            labels=label_list, assignees=assignee_list,
        )
        return json.dumps({
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "html_url": issue["html_url"],
            "message": f"Issue #{issue['number']} 已创建: {title}",
        }, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def github_update_issue(
        repo: str,
        issue_number: int,
        title: str = "",
        body: str = "",
        state: str = "",
        labels: str = "",
    ) -> str:
        """更新 GitHub 仓库上已有的 Issue。

        Args:
            repo: 仓库名（如 owner/repo）
            issue_number: Issue 编号
            title: 新标题（留空不修改）
            body: 新描述（留空不修改）
            state: 新状态：open / closed（留空不修改）
            labels: 新标签（逗号分隔，留空不修改）
        """
        label_list = [l.strip() for l in labels.split(",") if l.strip()] if labels else None
        issue = await client.update_issue(
            repo=repo, issue_number=issue_number,
            title=title or None, body=body or None,
            state=state or None, labels=label_list,
        )
        return json.dumps({
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "html_url": issue["html_url"],
            "message": f"Issue #{issue['number']} 已更新",
        }, ensure_ascii=False, indent=2)

    # ==================== 代码文件读取 ====================

    @mcp.tool()
    async def github_get_file(
        repo: str,
        file_path: str,
        ref: str = "",
    ) -> str:
        """读取 GitHub 仓库中的代码文件内容。

        Args:
            repo: 仓库名（如 owner/repo）
            file_path: 文件路径（如 src/main.py）
            ref: 分支名或 commit SHA，留空使用默认分支
        """
        file_data = await client.get_file(repo=repo, file_path=file_path, ref=ref)
        return json.dumps({
            "name": file_data.get("name", ""),
            "path": file_data.get("path", ""),
            "size": file_data.get("size", 0),
            "content": file_data.get("content", ""),
        }, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def github_search_code(
        repo: str,
        query: str,
    ) -> str:
        """在 GitHub 仓库代码中搜索关键词。

        Args:
            repo: 仓库名（如 owner/repo）
            query: 搜索关键词
        """
        results = await client.search_code(repo=repo, query=query)
        output = []
        for r in results:
            output.append({
                "name": r.get("name", ""),
                "path": r.get("path", ""),
                "html_url": r.get("html_url", ""),
            })
        return json.dumps(output, ensure_ascii=False, indent=2)

    # ==================== Actions (CI/CD) ====================

    @mcp.tool()
    async def github_get_actions(
        repo: str,
        status: str = "",
        per_page: int = 10,
    ) -> str:
        """获取 GitHub Actions 工作流运行记录。

        Args:
            repo: 仓库名（如 owner/repo）
            status: 状态筛选：completed / in_progress / queued，留空返回全部
            per_page: 返回条数，默认 10
        """
        runs = await client.get_workflow_runs(
            repo=repo, status=status or None, per_page=per_page,
        )
        result = []
        for r in runs:
            result.append({
                "id": r["id"],
                "name": r.get("name", ""),
                "status": r.get("status", ""),
                "conclusion": r.get("conclusion", ""),
                "branch": r.get("head_branch", ""),
                "created_at": r.get("created_at", ""),
                "html_url": r.get("html_url", ""),
            })
        return json.dumps(result, ensure_ascii=False, indent=2)
