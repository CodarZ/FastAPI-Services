import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.response.base import ErrorDetail

__all__ = [
    'BadRequestException',
    'BaseAppException',
    'ConflictException',
    'ForbiddenException',
    'NotFoundException',
    'ServiceUnavailableException',
    'TooManyRequestsException',
    'UnauthorizedException',
]

# 标准两段切分转换:
# 在「连续大写(acronym)后接小写」的转折处插下划线 (IPBlocked → IP_Blocked)
_CAMEL_ACRONYM = re.compile(r'([A-Z]+)([A-Z][a-z])')
# 在「小写/数字 → 大写」的转折处插下划线 (UserLock → User_Lock, V2Exceeded → V2_Exceeded)
_CAMEL_BOUNDARY = re.compile(r'([a-z\d])([A-Z])')


def _derive_canonical_code(class_name: str) -> str:
    """类名去 'Exception' 后缀, 转换分词."""
    name = class_name
    if name.endswith('Exception') and len(name) > len('Exception'):
        name = name[: -len('Exception')]
    name = _CAMEL_ACRONYM.sub(r'\1_\2', name)
    return _CAMEL_BOUNDARY.sub(r'\1_\2', name)


class BaseAppException(Exception):
    """业务异常基类.

    警告: 本基类不该直接使用

    - message: 提示文案
    - error_code: 资源级机器细码, 渲染到对应的 errors[].code
    - errors: 显式错误结构化明细, 优先于 error_code 合成
    - headers: 附加响应头 (如 Retry-After)
    """

    status_code: int = 500
    error_code: str | None = None  # 类级细码声明槽位 (None = 用类名推导保底); 实例属性经构造期解析恒为 str
    default_message: str = 'Internal server error.'

    def __init__(
        self,
        *,
        message: str | None = None,
        error_code: str | None = None,
        errors: list[ErrorDetail] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.error_code = (error_code or self.error_code or _derive_canonical_code(type(self).__name__)).upper()
        self.errors = errors
        self.headers = headers
        super().__init__(self.message)


class BadRequestException(BaseAppException):
    """请求语义非法 (400)."""

    status_code = 400
    default_message = 'Bad request.'


class UnauthorizedException(BaseAppException):
    """未认证 (401), 需携带 WWW-Authenticate 等质询头时用 headers."""

    status_code = 401
    default_message = 'Unauthorized.'


class ForbiddenException(BaseAppException):
    """已认证但权限不足 (403)."""

    status_code = 403
    default_message = 'Forbidden.'


class NotFoundException(BaseAppException):
    """资源不存在 (404)."""

    status_code = 404
    default_message = 'Resource not found.'


class ConflictException(BaseAppException):
    """资源状态冲突 (409), 如唯一键冲突、版本冲突."""

    status_code = 409
    default_message = 'Resource conflict.'


class TooManyRequestsException(BaseAppException):
    """触发限流 (429).

    headers 应携带退避指示:
        raise TooManyRequestsException(headers={'Retry-After': '30'})
    """

    status_code = 429
    default_message = 'Too many requests.'


class ServiceUnavailableException(BaseAppException):
    """依赖降级 / 暂不可用 (503), 可配 Retry-After."""

    status_code = 503
    default_message = 'Service temporarily unavailable.'
