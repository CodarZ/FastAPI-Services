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

# 驼峰命名分词 2 段正则
_CAMEL_ACRONYM = re.compile(r'([A-Z]+)([A-Z][a-z])')
_CAMEL_BOUNDARY = re.compile(r'([a-z\d])([A-Z])')


def _derive_canonical_code(class_name: str) -> str:
    """根据类名去 'Exception' 后缀, 转换分词为错误细码."""
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
    error_code: str | None = None
    message: str = 'Internal server error.'

    def __init__(
        self,
        *,
        message: str | None = None,
        error_code: str | None = None,
        errors: list[ErrorDetail] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.error_code = (error_code or self.error_code or _derive_canonical_code(type(self).__name__)).upper()
        self.errors = errors
        self.headers = headers
        super().__init__(self.message)


class BadRequestException(BaseAppException):
    """请求参数非法 (400)."""

    status_code = 400
    message = 'Bad request.'


class UnauthorizedException(BaseAppException):
    """未认证异常 (401)."""

    status_code = 401
    message = 'Unauthorized.'


class ForbiddenException(BaseAppException):
    """权限不足异常 (403)."""

    status_code = 403
    message = 'Forbidden.'


class NotFoundException(BaseAppException):
    """资源不存在异常 (404)."""

    status_code = 404
    message = 'Resource not found.'


class ConflictException(BaseAppException):
    """资源冲突异常 (409)."""

    status_code = 409
    message = 'Resource conflict.'


class TooManyRequestsException(BaseAppException):
    """请求过多异常 (429).

    headers 应携带退避指示:
        raise TooManyRequestsException(headers={'Retry-After': '30'})
    """

    status_code = 429
    message = 'Too many requests.'


class ServiceUnavailableException(BaseAppException):
    """服务暂不可用异常 (503), 可搭配 Retry-After."""

    status_code = 503
    message = 'Service temporarily unavailable.'
