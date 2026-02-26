"""
GitHub REST API 客户端

封装 GitHub API 的常用操作：提交记录、PR、Issue、代码文件等。
"""

import base64
from typing import Optional

import httpx
from loguru import logger


class GitHubClient:
    """GitHub REST API 异步客户端"""

    API_BASE = "https://api.github.com"

    def __init__(self, token: str, owner: str = ""):
        """
        初始化 GitHub 客户端

        Args:
            token: Personal Access Token（github_pat_ 开头）
            owner: 默认的仓库拥有者（用户名或组织名）
        """
        self.token = token
        self.owner = owner
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(
        self,
        method: str,
        path: str,
        params: dict = None,
        json_body: dict = None,
    ) -> dict | list:
        """发送 API 请求"""
        url = f"{self.API_BASE}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method, url, headers=self.headers, params=params, json=json_body
            )
            resp.raise_for_status()
            return resp.json()

    def _full_repo(self, repo: str) -> str:
        """
        补全仓库全名（owner/repo）

        如果传入的是短名（如 my-project），自动拼接默认 owner。
        如果已经是 owner/repo 格式，直接返回。
        """
        if "/" in repo:
            return repo
        if self.owner:
            return f"{self.owner}/{repo}"
        return repo

    # ==================== 仓库 ====================

    async def list_repos(self, per_page: int = 20) -> list[dict]:
        """获取当前用户的仓库列表"""
        params = {"per_page": per_page, "sort": "updated", "direction": "desc"}
        result = await self._request("GET", "/user/repos", params)
        logger.debug(f"获取到 {len(result)} 个仓库")
        return result

    async def search_repos(self, query: str, per_page: int = 10) -> list[dict]:
        """搜索仓库"""
        params = {"q": query, "per_page": per_page, "sort": "updated"}
        result = await self._request("GET", "/search/repositories", params)
        items = result.get("items", [])
        logger.debug(f"搜索到 {len(items)} 个仓库")
        return items

    async def get_repo(self, repo: str) -> dict:
        """获取仓库详情"""
        full = self._full_repo(repo)
        return await self._request("GET", f"/repos/{full}")

    # ==================== 提交记录 ====================

    async def get_commits(
        self,
        repo: str,
        branch: str = "",
        since: Optional[str] = None,
        until: Optional[str] = None,
        per_page: int = 20,
    ) -> list[dict]:
        """
        获取提交记录

        Args:
            repo: 仓库名（如 owner/repo 或短名）
            branch: 分支名（留空使用默认分支）
            since: 起始时间（ISO 8601 格式）
            until: 截止时间（ISO 8601 格式）
            per_page: 每页数量
        """
        full = self._full_repo(repo)
        params = {"per_page": per_page}
        if branch:
            params["sha"] = branch
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        result = await self._request("GET", f"/repos/{full}/commits", params)
        logger.info(f"获取到 {len(result)} 条提交记录 (仓库={full})")
        return result

    async def get_commit_detail(self, repo: str, sha: str) -> dict:
        """获取某次提交的详情（含 Diff）"""
        full = self._full_repo(repo)
        result = await self._request("GET", f"/repos/{full}/commits/{sha}")
        logger.info(f"获取到提交 {sha[:8]} 的详情 ({len(result.get('files', []))} 个文件变更)")
        return result

    # ==================== Pull Request ====================

    async def get_pull_requests(
        self,
        repo: str,
        state: str = "open",
        per_page: int = 20,
    ) -> list[dict]:
        """
        获取 Pull Request 列表

        Args:
            repo: 仓库名
            state: 状态筛选（open / closed / all）
            per_page: 每页数量
        """
        full = self._full_repo(repo)
        params = {"state": state, "per_page": per_page, "sort": "updated"}
        result = await self._request("GET", f"/repos/{full}/pulls", params)
        logger.info(f"获取到 {len(result)} 个 PR (仓库={full}, 状态={state})")
        return result

    # ==================== Issue 管理 ====================

    async def get_issues(
        self,
        repo: str,
        state: str = "open",
        labels: Optional[str] = None,
        per_page: int = 20,
    ) -> list[dict]:
        """
        获取 Issue 列表

        Args:
            repo: 仓库名
            state: 状态筛选（open / closed / all）
            labels: 标签筛选（逗号分隔）
            per_page: 每页数量
        """
        full = self._full_repo(repo)
        params = {"state": state, "per_page": per_page}
        if labels:
            params["labels"] = labels
        result = await self._request("GET", f"/repos/{full}/issues", params)
        # GitHub API 会把 PR 也当作 Issue 返回，需要过滤
        issues = [i for i in result if "pull_request" not in i]
        logger.info(f"获取到 {len(issues)} 个 Issue (仓库={full}, 状态={state})")
        return issues

    async def create_issue(
        self,
        repo: str,
        title: str,
        body: str = "",
        labels: Optional[list[str]] = None,
        assignees: Optional[list[str]] = None,
    ) -> dict:
        """
        创建 Issue

        Args:
            repo: 仓库名
            title: Issue 标题
            body: Issue 描述（支持 Markdown）
            labels: 标签列表
            assignees: 指派人用户名列表
        """
        full = self._full_repo(repo)
        json_body = {"title": title}
        if body:
            json_body["body"] = body
        if labels:
            json_body["labels"] = labels
        if assignees:
            json_body["assignees"] = assignees
        result = await self._request("POST", f"/repos/{full}/issues", json_body=json_body)
        logger.info(f"创建 Issue #{result['number']}: {title} (仓库={full})")
        return result

    async def update_issue(
        self,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> dict:
        """
        更新 Issue

        Args:
            repo: 仓库名
            issue_number: Issue 编号
            title: 新标题
            body: 新描述
            state: 状态（open / closed）
            labels: 新标签列表
        """
        full = self._full_repo(repo)
        json_body = {}
        if title:
            json_body["title"] = title
        if body is not None:
            json_body["body"] = body
        if state:
            json_body["state"] = state
        if labels is not None:
            json_body["labels"] = labels
        result = await self._request("PATCH", f"/repos/{full}/issues/{issue_number}", json_body=json_body)
        logger.info(f"更新 Issue #{issue_number} (仓库={full})")
        return result

    # ==================== 代码文件读取 ====================

    async def get_file(
        self,
        repo: str,
        file_path: str,
        ref: str = "",
    ) -> dict:
        """
        读取仓库中的文件内容

        Args:
            repo: 仓库名
            file_path: 文件路径
            ref: 分支名或 commit SHA（留空使用默认分支）
        """
        full = self._full_repo(repo)
        params = {}
        if ref:
            params["ref"] = ref
        result = await self._request("GET", f"/repos/{full}/contents/{file_path}", params)
        # GitHub 返回的 content 是 base64 编码的
        if result.get("content") and result.get("encoding") == "base64":
            # GitHub 返回的 base64 可能含换行符
            raw = result["content"].replace("\n", "")
            decoded = base64.b64decode(raw).decode("utf-8", errors="replace")
            result["content"] = decoded
        logger.info(f"读取文件: {file_path} (仓库={full})")
        return result

    async def get_repository_tree(
        self,
        repo: str,
        path: str = "",
        ref: str = "",
    ) -> list[dict]:
        """
        获取仓库目录内容

        Args:
            repo: 仓库名
            path: 目录路径（留空获取根目录）
            ref: 分支名
        """
        full = self._full_repo(repo)
        api_path = f"/repos/{full}/contents/{path}" if path else f"/repos/{full}/contents"
        params = {}
        if ref:
            params["ref"] = ref
        result = await self._request("GET", api_path, params)
        if isinstance(result, dict):
            result = [result]
        logger.info(f"获取目录: {path or '/'} (仓库={full}, {len(result)} 项)")
        return result

    async def search_code(
        self,
        repo: str,
        query: str,
    ) -> list[dict]:
        """
        在仓库中搜索代码

        Args:
            repo: 仓库名
            query: 搜索关键词
        """
        full = self._full_repo(repo)
        search_query = f"{query} repo:{full}"
        params = {"q": search_query, "per_page": 20}
        result = await self._request("GET", "/search/code", params)
        items = result.get("items", [])
        logger.info(f"代码搜索: '{query}' 在 {full} 中找到 {len(items)} 个结果")
        return items

    # ==================== Actions (CI/CD) ====================

    async def get_workflow_runs(
        self,
        repo: str,
        status: Optional[str] = None,
        per_page: int = 10,
    ) -> list[dict]:
        """
        获取 GitHub Actions 工作流运行记录

        Args:
            repo: 仓库名
            status: 状态筛选（completed / in_progress / queued）
            per_page: 每页数量
        """
        full = self._full_repo(repo)
        params = {"per_page": per_page}
        if status:
            params["status"] = status
        result = await self._request("GET", f"/repos/{full}/actions/runs", params)
        runs = result.get("workflow_runs", [])
        logger.info(f"获取到 {len(runs)} 条 Actions 记录 (仓库={full})")
        return runs

    # ==================== GraphQL（Projects V2 必需） ====================

    GRAPHQL_URL = "https://api.github.com/graphql"

    async def _graphql(self, query: str, variables: dict = None) -> dict:
        """发送 GraphQL 请求"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.GRAPHQL_URL, headers=self.headers, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                logger.error(f"GraphQL 错误: {data['errors']}")
                raise Exception(f"GraphQL Error: {data['errors'][0].get('message', '')}")
            return data.get("data", {})

    # ==================== Projects V2 看板 ====================

    async def list_projects(self, per_page: int = 20) -> list[dict]:
        """
        列出当前用户的所有 GitHub Projects V2

        Returns:
            项目列表，每项包含 id, number, title, url
        """
        query = """
        query($login: String!, $first: Int!) {
          user(login: $login) {
            projectsV2(first: $first, orderBy: {field: UPDATED_AT, direction: DESC}) {
              nodes {
                id
                number
                title
                shortDescription
                url
                closed
              }
            }
          }
        }
        """
        data = await self._graphql(query, {"login": self.owner, "first": per_page})
        projects = data.get("user", {}).get("projectsV2", {}).get("nodes", [])
        logger.info(f"获取到 {len(projects)} 个 Project")
        return projects

    async def get_project_by_name(self, name: str) -> dict | None:
        """
        通过名称模糊匹配查找 Project

        Args:
            name: 项目名称（支持模糊匹配）

        Returns:
            匹配到的 Project，未找到返回 None
        """
        projects = await self.list_projects(per_page=50)
        name_lower = name.lower().strip()
        # 精确匹配
        for p in projects:
            if p["title"].lower() == name_lower:
                logger.info(f"精确匹配 Project: {p['title']} (ID: {p['id']})")
                return p
        # 模糊匹配
        for p in projects:
            if name_lower in p["title"].lower():
                logger.info(f"模糊匹配 Project: {p['title']} (ID: {p['id']})")
                return p
        logger.warning(f"未找到 Project: {name}")
        return None

    async def add_issue_to_project(
        self,
        project_id: str,
        issue_node_id: str,
    ) -> dict:
        """
        将 Issue 添加到 Project 看板

        Args:
            project_id: Project 的 GraphQL Node ID
            issue_node_id: Issue 的 GraphQL Node ID

        Returns:
            添加结果，包含 item ID
        """
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item {
              id
            }
          }
        }
        """
        data = await self._graphql(mutation, {
            "projectId": project_id,
            "contentId": issue_node_id,
        })
        item = data.get("addProjectV2ItemById", {}).get("item", {})
        logger.info(f"Issue 已添加到 Project (item_id={item.get('id', '')})")
        return item

    async def get_issue_node_id(self, repo: str, issue_number: int) -> str:
        """
        获取 Issue 的 GraphQL Node ID（用于 Projects V2 操作）

        Args:
            repo: 仓库名
            issue_number: Issue 编号
        """
        full = self._full_repo(repo)
        owner, name = full.split("/", 1)
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $number) {
              id
            }
          }
        }
        """
        data = await self._graphql(query, {
            "owner": owner, "repo": name, "number": issue_number,
        })
        node_id = data.get("repository", {}).get("issue", {}).get("id", "")
        logger.debug(f"Issue #{issue_number} Node ID: {node_id}")
        return node_id

