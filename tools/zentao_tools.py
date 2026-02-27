"""
禅道 MCP Tools

注册与禅道相关的 MCP 工具：Bug 管理、任务管理、需求查询。
"""

import json

from mcp.server.fastmcp import FastMCP

from clients.zentao_client import ZentaoClient


def register_zentao_tools(mcp: FastMCP, client: ZentaoClient):
    """将禅道工具注册到 MCP Server"""

    @mcp.tool()
    async def zentao_list_products() -> str:
        """获取禅道产品列表。"""
        products = await client.list_products()
        return json.dumps(products, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def zentao_list_projects() -> str:
        """获取禅道项目列表。"""
        projects = await client.list_projects()
        return json.dumps(projects, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def zentao_list_bugs(
        product_id: int,
        status: str = "",
        assignedTo: str = "",
        per_page: int = 20,
    ) -> str:
        """获取禅道 Bug 列表。

        Args:
            product_id: 产品 ID（可通过 zentao_list_products 获取）
            status: 状态筛选（active/resolved/closed），留空返回全部
            assignedTo: 指派人筛选，留空返回全部
            per_page: 返回条数，默认 20
        """
        bugs = await client.list_bugs(
            product_id=product_id,
            status=status,
            assignedTo=assignedTo,
            limit=per_page,
        )
        return json.dumps(bugs, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def zentao_get_bug(bug_id: int) -> str:
        """获取禅道 Bug 详情。

        Args:
            bug_id: Bug ID
        """
        bug = await client.get_bug(bug_id)
        return json.dumps(bug, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def zentao_create_bug(
        product_id: int,
        title: str,
        steps: str = "",
        severity: int = 3,
        pri: int = 3,
        bug_type: str = "codeerror",
        assignedTo: str = "",
    ) -> str:
        """在禅道创建一个 Bug。

        Args:
            product_id: 产品 ID
            title: Bug 标题
            steps: 重现步骤（支持 HTML 格式）
            severity: 严重程度（1=致命, 2=严重, 3=一般, 4=轻微）
            pri: 优先级（1=紧急, 2=高, 3=中, 4=低）
            bug_type: Bug 类型（codeerror/designdefect/config/install/security/performance/standard/automation/other）
            assignedTo: 指派人账号名
        """
        result = await client.create_bug(
            product_id=product_id,
            title=title,
            steps=steps,
            severity=severity,
            pri=pri,
            bug_type=bug_type,
            assignedTo=assignedTo,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def zentao_list_tasks(
        execution_id: int,
        status: str = "",
        per_page: int = 20,
    ) -> str:
        """获取禅道任务列表。

        Args:
            execution_id: 执行（迭代）ID
            status: 状态筛选（wait/doing/done/closed），留空返回全部
            per_page: 返回条数，默认 20
        """
        tasks = await client.list_tasks(
            execution_id=execution_id,
            status=status,
            limit=per_page,
        )
        return json.dumps(tasks, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def zentao_create_task(
        execution_id: int,
        name: str,
        assignedTo: str = "",
        estimate: float = 0,
        pri: int = 3,
        desc: str = "",
    ) -> str:
        """在禅道创建一个任务。

        Args:
            execution_id: 执行（迭代）ID
            name: 任务名称
            assignedTo: 指派人账号名
            estimate: 预计工时（小时）
            pri: 优先级（1=紧急, 2=高, 3=中, 4=低）
            desc: 任务描述
        """
        result = await client.create_task(
            execution_id=execution_id,
            name=name,
            assignedTo=assignedTo,
            estimate=estimate,
            pri=pri,
            desc=desc,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def zentao_list_stories(
        product_id: int,
        status: str = "",
        per_page: int = 20,
    ) -> str:
        """获取禅道需求列表。

        Args:
            product_id: 产品 ID（可通过 zentao_list_products 获取）
            status: 状态筛选（draft/active/closed/changed），留空返回全部
            per_page: 返回条数，默认 20
        """
        stories = await client.list_stories(
            product_id=product_id,
            status=status,
            limit=per_page,
        )
        return json.dumps(stories, ensure_ascii=False, indent=2)
