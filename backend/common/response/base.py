from pydantic import BaseModel, Field

__all__ = [
    'PageResult',
    'ResponseModel',
    'response_base',
]


class ResponseModel[T](BaseModel):
    """全局统一 API 响应模型."""

    code: int = Field(default=200, description='业务状态码')
    message: str = Field(default='请求成功', description='提示信息')
    data: T | None = Field(default=None, description='响应业务载荷')
    trace_id: str | None = Field(default=None, description='全链路追踪 ID (仅开发/测试环境返回)')


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
        return ResponseModel[T](code=code, message=message, data=data, trace_id=trace_id)


response_base = ResponseBase()
