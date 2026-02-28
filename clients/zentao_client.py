"""
禅道（ZenTao）REST API 异步客户端

封装禅道 API v1 的认证、Bug、任务、需求等操作。
"""


import httpx
from loguru import logger

from clients.exceptions import ZentaoAPIError


class ZentaoClient:
    """禅道 REST API 异步客户端"""

    def __init__(self, url: str, account: str, password: str):
        """
        初始化禅道客户端

        Args:
            url: 禅道访问地址（如 http://erp.yiyinwen.com:18088/zentao）
            account: 登录账号
            password: 登录密码
        """
        # 去掉末尾斜杠，拼接 API 前缀
        self.base_url = url.rstrip("/")
        self.api_url = f"{self.base_url}/api.php/v1"
        self.account = account
        self.password = password
        self._token: str | None = None
        self._client = httpx.AsyncClient(timeout=30)

    # ==================== 认证 ====================

    async def _ensure_token(self) -> None:
        """确保已获取有效的 Token（懒加载 + 缓存）"""
        if self._token:
            return
        try:
            response = await self._client.post(
                f"{self.api_url}/tokens",
                json={"account": self.account, "password": self.password},
            )
            response.raise_for_status()
            data = response.json()
            self._token = data.get("token")
            if not self._token:
                raise ValueError(f"禅道登录失败，响应: {data}")
            logger.info(f"禅道登录成功: {self.account}")
        except httpx.HTTPError as e:
            logger.error(f"禅道登录失败: {e}")
            raise ZentaoAPIError(f"禅道登录失败: {e}", cause=e) from e

    def _headers(self) -> dict:
        """构建带 Token 的请求头"""
        return {"Token": self._token or ""}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """发送 GET 请求"""
        await self._ensure_token()
        url = f"{self.api_url}{path}"
        try:
            response = await self._client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Token 过期时重新登录
            if e.response.status_code == 401:
                logger.warning("禅道 Token 过期，重新登录...")
                self._token = None
                await self._ensure_token()
                response = await self._client.get(url, headers=self._headers(), params=params)
                response.raise_for_status()
                return response.json()
            raise

    async def _post(self, path: str, json_data: dict) -> dict:
        """发送 POST 请求"""
        await self._ensure_token()
        url = f"{self.api_url}{path}"
        try:
            response = await self._client.post(url, headers=self._headers(), json=json_data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("禅道 Token 过期，重新登录...")
                self._token = None
                await self._ensure_token()
                response = await self._client.post(url, headers=self._headers(), json=json_data)
                response.raise_for_status()
                return response.json()
            raise

    async def _put(self, path: str, json_data: dict) -> dict:
        """发送 PUT 请求"""
        await self._ensure_token()
        url = f"{self.api_url}{path}"
        try:
            response = await self._client.put(url, headers=self._headers(), json=json_data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("禅道 Token 过期，重新登录...")
                self._token = None
                await self._ensure_token()
                response = await self._client.put(url, headers=self._headers(), json=json_data)
                response.raise_for_status()
                return response.json()
            raise

    # ==================== 产品 ====================

    async def list_products(self, limit: int = 50) -> list[dict]:
        """获取产品列表"""
        data = await self._get("/products", params={"limit": limit})
        products = data.get("products", [])
        logger.info(f"获取到 {len(products)} 个产品")
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "status": p["status"],
                "bugs": p.get("bugs", 0),
                "unResolved": p.get("unResolved", 0),
            }
            for p in products
        ]

    # ==================== 项目 ====================

    async def list_projects(self, limit: int = 50) -> list[dict]:
        """获取项目列表"""
        data = await self._get("/projects", params={"limit": limit})
        projects = data.get("projects", [])
        logger.info(f"获取到 {len(projects)} 个项目")
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "status": p["status"],
                "begin": p.get("begin", ""),
                "end": p.get("end", ""),
                "PM": p.get("PM", {}).get("realname", "") if isinstance(p.get("PM"), dict) else str(p.get("PM", "")),
            }
            for p in projects
        ]

    # ==================== Bug ====================

    async def list_bugs(
        self,
        product_id: int,
        status: str = "",
        assignedTo: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """
        获取 Bug 列表

        Args:
            product_id: 产品 ID
            status: 状态筛选（active/resolved/closed），留空返回全部
            assignedTo: 指派人筛选，留空返回全部
            limit: 返回条数
        """
        params: dict = {"limit": limit}
        if status:
            params["status"] = status
        if assignedTo:
            params["assignedTo"] = assignedTo

        data = await self._get(f"/products/{product_id}/bugs", params=params)
        bugs = data.get("bugs", [])
        logger.info(f"获取到 {len(bugs)} 个 Bug（产品 {product_id}）")
        return [
            {
                "id": b["id"],
                "title": b["title"],
                "status": b["status"],
                "severity": b.get("severity", ""),
                "pri": b.get("pri", ""),
                "assignedTo": b.get("assignedTo", {}).get("realname", "") if isinstance(b.get("assignedTo"), dict) else str(b.get("assignedTo", "")),
                "openedBy": b.get("openedBy", {}).get("realname", "") if isinstance(b.get("openedBy"), dict) else str(b.get("openedBy", "")),
                "openedDate": b.get("openedDate", ""),
            }
            for b in bugs
        ]

    async def get_bug(self, bug_id: int) -> dict:
        """获取 Bug 详情"""
        data = await self._get(f"/bugs/{bug_id}")
        logger.info(f"获取 Bug 详情: #{bug_id} {data.get('title', '')}")
        return data

    async def create_bug(
        self,
        product_id: int,
        title: str,
        steps: str = "",
        severity: int = 3,
        pri: int = 3,
        bug_type: str = "codeerror",
        assignedTo: str = "",
    ) -> dict:
        """
        创建 Bug

        Args:
            product_id: 产品 ID
            title: Bug 标题
            steps: 重现步骤（支持 HTML 格式）
            severity: 严重程度（1=致命, 2=严重, 3=一般, 4=轻微）
            pri: 优先级（1=紧急, 2=高, 3=中, 4=低）
            bug_type: Bug 类型（codeerror/designdefect/config/install/security/performance/standard/automation/other）
            assignedTo: 指派人账号名
        """
        body: dict = {
            "product": product_id,
            "title": title,
            "steps": steps,
            "severity": severity,
            "pri": pri,
            "type": bug_type,
        }
        if assignedTo:
            body["assignedTo"] = assignedTo

        data = await self._post(f"/products/{product_id}/bugs", json_data=body)
        logger.info(f"Bug 已创建: #{data.get('id', '')} {title}")
        return data

    async def update_bug(self, bug_id: int, **kwargs) -> dict:
        """
        更新 Bug

        Args:
            bug_id: Bug ID
            **kwargs: 要更新的字段（如 status, assignedTo, severity 等）
        """
        data = await self._put(f"/bugs/{bug_id}", json_data=kwargs)
        logger.info(f"Bug #{bug_id} 已更新")
        return data

    # ==================== 任务 ====================

    async def get_task(self, task_id: int) -> dict:
        """
        获取任务详情

        Args:
            task_id: 任务 ID
        """
        data = await self._get(f"/tasks/{task_id}")
        logger.info(f"已获取任务 #{task_id} 详情")
        return data

    async def list_tasks(
        self,
        execution_id: int,
        status: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """
        获取任务列表

        Args:
            execution_id: 执行（迭代）ID
            status: 状态筛选（wait/doing/done/closed），留空返回全部
            limit: 返回条数
        """
        params: dict = {"limit": limit}
        if status:
            params["status"] = status

        data = await self._get(f"/executions/{execution_id}/tasks", params=params)
        tasks = data.get("tasks", [])
        logger.info(f"获取到 {len(tasks)} 个任务（执行 {execution_id}）")
        return [
            {
                "id": t["id"],
                "name": t["name"],
                "status": t["status"],
                "pri": t.get("pri", ""),
                "assignedTo": t.get("assignedTo", {}).get("realname", "") if isinstance(t.get("assignedTo"), dict) else str(t.get("assignedTo", "")),
                "deadline": t.get("deadline", ""),
                "estimate": t.get("estimate", 0),
            }
            for t in tasks
        ]

    async def create_task(
        self,
        execution_id: int,
        name: str,
        assignedTo: str = "",
        estimate: float = 0,
        pri: int = 3,
        desc: str = "",
    ) -> dict:
        """
        创建任务

        Args:
            execution_id: 执行（迭代）ID
            name: 任务名称
            assignedTo: 指派人账号名
            estimate: 预计工时（小时）
            pri: 优先级（1=紧急, 2=高, 3=中, 4=低）
            desc: 任务描述
        """
        body: dict = {
            "name": name,
            "pri": pri,
            "estimate": estimate,
        }
        if assignedTo:
            body["assignedTo"] = assignedTo
        if desc:
            body["desc"] = desc

        data = await self._post(f"/executions/{execution_id}/tasks", json_data=body)
        logger.info(f"任务已创建: #{data.get('id', '')} {name}")
        return data

    # ==================== 需求 ====================

    async def list_stories(
        self,
        product_id: int,
        status: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """
        获取需求列表

        Args:
            product_id: 产品 ID
            status: 状态筛选（draft/active/closed/changed），留空返回全部
            limit: 返回条数
        """
        params: dict = {"limit": limit}
        if status:
            params["status"] = status

        data = await self._get(f"/products/{product_id}/stories", params=params)
        stories = data.get("stories", [])
        logger.info(f"获取到 {len(stories)} 个需求（产品 {product_id}）")
        return [
            {
                "id": s["id"],
                "title": s["title"],
                "status": s["status"],
                "pri": s.get("pri", ""),
                "stage": s.get("stage", ""),
                "assignedTo": s.get("assignedTo", {}).get("realname", "") if isinstance(s.get("assignedTo"), dict) else str(s.get("assignedTo", "")),
            }
            for s in stories
        ]
