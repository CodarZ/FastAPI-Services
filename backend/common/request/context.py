from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic_ns
from typing import TYPE_CHECKING, Any

from backend.common.request.trace_id import gen_trace_id
from backend.core.config import settings

if TYPE_CHECKING:
    from backend.common.model.dataclasses import (
        ClientContext,
        DataScopeContext,
        TenantContext,
        UserIdentity,
    )

__all__ = [
    'RequestContext',
    'bind_context',
    'ctx',
    'get_request_context',
]

# 未解析到客户端 IP 时的占位符，杜绝 None 穿透至字符串处理函数
_UNKNOWN_IP: str = '0.0.0.0'  # nosec B104


@dataclass(slots=True)
class RequestContext:
    """单次请求 / 单个异步任务生命周期内的上下文容器."""

    trace_id: str
    client: ClientContext | None = None  # 客户端快照 (IP、UA、属地)
    tenant: TenantContext | None = None  # 当前绑定的租户上下文
    user: UserIdentity | None = None  # 鉴权用户
    data_scope: DataScopeContext | None = None  # 当前用户的数据权限
    extra: dict[str, Any] = field(default_factory=dict)  # 扩展字典
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))  # 请求/任务进入的挂钟时间 (UTC)
    start_time_ns: int = field(default_factory=monotonic_ns)  # 请求/任务进入的单调时间 (耗时计算唯一可信来源)


# 协程请求上下文 ContextVar 单例
_request_ctx: ContextVar[RequestContext | None] = ContextVar('request_ctx', default=None)


class _ContextProxy:
    """请求上下文 代理单例 (读宽写严原则).

    - 读宽 (Read-Lax): 脱离请求上下文读取属性时返回确定的安全默认值，永不抛出 AttributeError 异常；
    - 写严 (Write-Strict): 脱离上下文尝试写入时抛出 RuntimeError，坚决阻断隐式状态丢失与跨协程污染。
    """

    __slots__ = ()

    @property
    def raw(self) -> RequestContext | None:
        """获取当前底层 RequestContext 原始容器实例 (未绑定时返回 None)."""
        return _request_ctx.get()

    @property
    def is_bound(self) -> bool:
        """检查当前协程上下文是否已正确绑定."""
        return _request_ctx.get() is not None

    @property
    def trace_id(self) -> str:
        """获取 Trace ID."""
        rc = _request_ctx.get()
        return rc.trace_id if rc else settings.TRACE_ID_LOG_DEFAULT

    @property
    def client(self) -> ClientContext | None:
        """获取客户端快照 (IP、UA、属地)."""
        rc = _request_ctx.get()
        return rc.client if rc else None

    @property
    def ip(self) -> str:
        """获取客户端真实 IP."""
        client = self.client
        return client.ip if client and client.ip else _UNKNOWN_IP

    @property
    def user_agent(self) -> str | None:
        """获取原始 User-Agent."""
        client = self.client
        return client.user_agent if client else None

    @property
    def tenant(self) -> TenantContext | None:
        """获取当前租户上下文."""
        rc = _request_ctx.get()
        return rc.tenant if rc else None

    @property
    def tenant_id(self) -> str | None:
        """获取当前租户 UID."""
        tenant = self.tenant
        return tenant.tenant_id if tenant else None

    @property
    def schema_name(self) -> str:
        """获取当前绑定的 PostgreSQL 物理 Schema 名称 (未绑定时回退至公共 Schema)."""
        tenant = self.tenant
        return tenant.schema_name if tenant else settings.TENANT_DEFAULT_SCHEMA

    @property
    def user(self) -> UserIdentity | None:
        """获取当前鉴权的用户信息."""
        rc = _request_ctx.get()
        return rc.user if rc else None

    @property
    def user_uid(self) -> str | None:
        """获取当前登录用户的公开业务短 UID (未登录或未绑定返回 None).

        供访问审计日志与 Celery 跨进程透传 X-Operator-UID 直接使用，
        免去调用方反复书写 ctx.user.uid if ctx.user else None 的空指针判定。
        """
        user = self.user
        return user.uid if user else None

    @property
    def data_scope(self) -> DataScopeContext | None:
        """获取当前用户的数据权限."""
        rc = _request_ctx.get()
        return rc.data_scope if rc else None

    @property
    def start_time_ns(self) -> int | None:
        """获取请求进入系统的 monotonic 纳秒时间戳 (未绑定时返回 None).

        使用单调时钟而非挂钟时间，避免 NTP 校时回拨导致耗时计算出现负值。
        """
        rc = _request_ctx.get()
        return rc.start_time_ns if rc else None

    def get_extra(self, key: str, default: Any = None) -> Any:
        """获取自定义扩展字段."""
        rc = _request_ctx.get()
        return rc.extra.get(key, default) if rc else default

    def set_user(self, user: UserIdentity) -> None:
        """更新用户上下文."""
        self._require().user = user

    def set_tenant(self, tenant: TenantContext) -> None:
        """更新租户上下文."""
        self._require().tenant = tenant

    def set_data_scope(self, data_scope: DataScopeContext) -> None:
        """更新数据权限上下文."""
        self._require().data_scope = data_scope

    def set_extra(self, key: str, value: Any) -> None:
        """更新扩展字典."""
        self._require().extra[key] = value

    @staticmethod
    def _require() -> RequestContext:
        rc = _request_ctx.get()
        if rc is None:
            raise RuntimeError('请求上下文尚未绑定，严禁在脱离上下文的作用域内执行写入操作')
        return rc


# 全局唯一的强类型代理单例
ctx = _ContextProxy()


class _ContextBindingManager:
    """请求上下文生命周期管理器.

    支持同步 with 与异步 async with 双协议.
    """

    __slots__ = ('_ctx_obj', '_token')

    def __init__(self, ctx_obj: RequestContext) -> None:
        self._ctx_obj: RequestContext = ctx_obj
        self._token: Token[RequestContext | None] | None = None

    def __enter__(self) -> RequestContext:
        self._token = _request_ctx.set(self._ctx_obj)
        return self._ctx_obj

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._token is not None:
            _request_ctx.reset(self._token)
            self._token = None

    async def __aenter__(self) -> RequestContext:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)


def bind_context(
    trace_id: str | None = None,
    *,
    client: ClientContext | None = None,
    tenant: TenantContext | None = None,
    user: UserIdentity | None = None,
    data_scope: DataScopeContext | None = None,
) -> _ContextBindingManager:
    """绑定一个新的请求上下文生命周期 (退出时严格 reset 还原父级状态)."""
    return _ContextBindingManager(
        RequestContext(
            trace_id=trace_id or gen_trace_id(),
            client=client,
            tenant=tenant,
            user=user,
            data_scope=data_scope,
        )
    )


def get_request_context() -> RequestContext:
    """FastAPI 依赖注入: 获取当前经过显式绑定的 RequestContext 实例.

    未绑定上下文时抛出 RuntimeError。
    """
    rc = _request_ctx.get()
    if rc is None:
        raise RuntimeError('请求上下文尚未绑定，请确认相关追踪中间件已正确挂载')
    return rc
