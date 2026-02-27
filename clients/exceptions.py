"""
DevOps Agent 自定义异常体系

统一所有客户端的异常处理，便于上层捕获和分类处理。
"""


class DevOpsAgentError(Exception):
    """DevOps Agent 基础异常"""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class GitHubAPIError(DevOpsAgentError):
    """GitHub API 调用异常"""

    def __init__(self, message: str, status_code: int = 0, cause: Exception | None = None):
        super().__init__(message, cause)
        self.status_code = status_code


class SlackAPIError(DevOpsAgentError):
    """Slack API 调用异常"""

    def __init__(self, message: str, error_code: str = "", cause: Exception | None = None):
        super().__init__(message, cause)
        self.error_code = error_code


class ZentaoAPIError(DevOpsAgentError):
    """禅道 API 调用异常"""

    def __init__(self, message: str, status_code: int = 0, cause: Exception | None = None):
        super().__init__(message, cause)
        self.status_code = status_code
