from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    'ErrorDetail',
    'PageResult',
    'ResponseBase',
    'ResponseModel',
    'response_base',
]


class ErrorDetail(BaseModel):
    """结构化错误明细.

    - field: RFC 6901 JSON Pointer 字段定位; 全局项与空 loc 为 None
    - code: 资源级机器细码 (如 'USER_NOT_FOUND'); 全局项由异常 error_code 合成
    - message: 全局项与 production 422 明细为 None
    - type: pydantic 校验类型等机器类型标识
    """

    field: str | None = None
    code: str | None = None
    message: str | None = None
    type: str | None = None


class ResponseModel[T](BaseModel):
    """全局统一 API 响应模型."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    code: int = Field(default=200, description='HTTP 状态码对齐的业务语义')
    message: str = Field(default='请求成功', description='提示信息')
    data: T | None = Field(default=None, description='响应业务载荷')
    trace_id: str | None = Field(default=None, description='全链路追踪 ID')
    errors: list[ErrorDetail] | None = Field(default=None, description='结构化错误明细')


class PageResult[T](BaseModel):
    """分页载荷."""

    items: list[T] = Field(default_factory=list, description='当前页数据列表')
    total: int = Field(description='总记录数')
    page: int = Field(description='当前页码')
    page_size: int = Field(description='每页条数')
    total_pages: int = Field(description='总页数')


class ResponseBase:
    """快捷响应."""

    @staticmethod
    def success[T](
        data: T | None = None,
        *,
        message: str = '请求成功',
        code: int = 200,
        trace_id: str | None = None,
    ) -> ResponseModel[T]:
        return ResponseModel[T](code=code, message=message, data=data, trace_id=trace_id, errors=None)

    @staticmethod
    def fail(
        *,
        message: str = '请求处理失败',
        code: int = 400,
        errors: list[ErrorDetail] | None = None,
        trace_id: str | None = None,
    ) -> ResponseModel[None]:
        return ResponseModel[None](code=code, message=message, data=None, trace_id=trace_id, errors=errors)


response_base = ResponseBase()
