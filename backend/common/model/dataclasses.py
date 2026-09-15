from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
    'AccessLogRecord',
    'AccessTokenPayload',
    'ClientContext',
    'DataScopeContext',
    'ImpersonationContext',
    'OutboxEventRecord',
    'RefreshTokenPayload',
    'TaskContext',
    'TenantContext',
    'TraceContext',
    'UserAgentInfo',
    'UserIdentity',
]


@dataclass(frozen=True, slots=True)
class ClientContext:
    """客户端连接元数据.

    使用场景:
    - Trace 中间件在请求入口提取并绑定至 ctx.client
    - 访问日志与安全风控模块读取客户端来源
    """

    ip: str | None = None
    user_agent: str | None = None
    ip_region: str | None = None  # IP 离线解析属地 (如 '中国|广东省|深圳市|电信')


@dataclass(frozen=True, slots=True)
class UserAgentInfo:
    """结构化 User-Agent 解析信息.

    使用场景:
    - 登录日志记录终端环境
    - 异常设备访问风控拦截与多端适配
    """

    raw: str | None = None
    browser: str | None = None
    os: str | None = None
    device: str | None = None
    is_mobile: bool = False
    is_tablet: bool = False  # 平板
    is_pc: bool = False
    is_bot: bool = False  # 爬虫或机器探测


@dataclass(frozen=True, slots=True)
class TraceContext:
    """全链路追踪上下文.

    使用场景:
    - 请求入口初始化并注入 Loguru 日志 extra[request_id]
    - 跨服务 HTTP 调用及 Celery 任务下发透传
    """

    trace_id: str
    span_id: str  # 当前调用跨度 ID
    parent_span_id: str | None = None  # 上游调用跨度 ID (顶级入口为 None)


@dataclass(frozen=True, slots=True)
class TenantContext:
    """租户上下文.

    使用场景:
    - JWT 鉴权后注入 ctx.tenant
    - 会话工厂 get_tenant_db 动态配置 schema_translate_map
    """

    tenant_id: str  # 租户公开业务短 UID
    schema_name: str  # PostgreSQL 物理 Schema 名 (如 'tenant_xxx')
    is_fallback: bool = False  # 是否处于单租户回退模式 (True 时物理 Schema 为 public)


@dataclass(frozen=True, slots=True)
class AccessTokenPayload:
    """Access Token 鉴权载荷."""

    sub: str  # 用户内部账号 (Subject)
    uid: str  # 用户公开业务短 UID (对外接口使用)
    tenant_id: str | None  # 所属租户 UID (单租户或平台超管为 None)
    audience: str  # JWT 受众通道 (fs:admin 管理端 / fs:client 客户端)
    token_version: int  # 令牌版本号 (修改密码或禁用时递增，用于秒级全端吊销)
    exp: datetime  # 令牌过期绝对时间 (UTC)


@dataclass(frozen=True, slots=True)
class RefreshTokenPayload:
    """Refresh Token 刷新凭证."""

    sub: str  # 用户内部账号
    uid: str  # 用户公开业务短 UID
    tenant_id: str | None  # 所属租户 UID
    audience: str  # JWT 受众通道 (fs:admin / fs:client)
    token_version: int  # 令牌版本号
    exp: datetime  # 刷新凭证过期绝对时间 (UTC)


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """当前登录用户信息.

    使用场景:
    - 鉴权依赖项验证通过后注入 ctx.set_user
    - Controller / Service 获取当前操作人与权限判定
    """

    uid: str  # 用户公开业务短 UID
    sub: str  # 用户内部账号
    tenant_id: str | None = None  # 所属租户 UID
    dept_id: int | None = None  # 所属部门内部物理主键 ID
    is_superuser: bool = False  # 是否为拥有全平台特权的超级管理员
    roles: frozenset[str] = field(default_factory=frozenset)  # 角色编码集合
    permissions: frozenset[str] = field(default_factory=frozenset)  # 按钮与接口权限标识集合


@dataclass(frozen=True, slots=True)
class DataScopeContext:
    """行级数据权限.

    使用场景:
    - RBAC 权限拦截器解析当前用户数据权限
    - 仓储层动态拼装部门及本人 SQL 约束
    """

    scope_type: int  # 权限范围类型 (对应 DataScopeType 枚举)
    user_id: int  # 操作人内部物理主键 ID (用于仅本人数据过滤)
    dept_id: int | None = None  # 操作人所属部门物理主键 ID
    target_dept_ids: frozenset[int] = field(default_factory=frozenset)  # 经授权允许访问的目标部门 ID 集合


@dataclass(frozen=True, slots=True)
class TaskContext:
    """异步任务跨进程上下文.

    使用场景:
    - Web 端调度 Celery 异步任务时写入 Headers
    - Worker 消费端还原 TraceID 与租户环境
    """

    trace_id: str  # 原始 HTTP 请求 Trace ID
    tenant_id: str | None = None  # 发起任务时的租户 UID
    operator_uid: str | None = None  # 发起任务的操作人 UID
    dispatched_at: datetime | None = None  # 任务下发时间 (UTC)


@dataclass(frozen=True, slots=True)
class OutboxEventRecord:
    """事务性发件箱 (Outbox) 事件内存契约.

    使用场景:
    - 领域服务在本地事务中与业务数据原子入库
    - 异步分发 Worker 提取并广播领域事件
    """

    event_id: str  # 事件全局唯一 ID (如 uuid7)
    event_type: str  # 事件业务主题 (如 'user.created', 'order.paid')
    aggregate_type: str  # 领域聚合根名称 (如 'user', 'tenant')
    aggregate_id: str  # 领域聚合根公开业务 UID
    payload: str  # 事件主体 JSON 序列化字符串
    trace_id: str  # 触发该事件的链路追踪 ID
    tenant_id: str | None = None  # 所属租户 UID
    occurred_at: datetime | None = None  # 事件产生时间戳 (UTC)


@dataclass(frozen=True, slots=True)
class AccessLogRecord:
    """访问日志审计.

    使用场景:
    - 请求访问日志中间件汇总请求耗时与状态码
    - 异步提交后台审计日志流或监控指标
    """

    trace_id: str
    method: str
    path: str  # 实际请求地址路径
    status_code: int
    process_time_ms: float  # 请求处理耗时 (毫秒)
    reason: str | None = None  # 响应
    client_ip: str | None = None  # 客户端真实 IP
    user_uid: str | None = None  # 操作人业务 UID (未登录为 None)
    tenant_id: str | None = None  # 租户 UID
    user_agent: str | None = None  # 原始 UA
    occurred_at: datetime | None = None  # 请求完成时间戳 (UTC)


@dataclass(frozen=True, slots=True)
class ImpersonationContext:
    """平台超管代客操作审计.

    使用场景:
    - 超管代客排查接口构建会话凭据
    - 跨租户运维操作合规审计落盘
    """

    impersonator_uid: str  # 发起代客操作的超管 UID
    target_tenant_id: str  # 被代客访问的目标租户 UID
    reason: str  # 代客操作工单编号或审批事由
    started_at: datetime  # 代客接入建立时间 (UTC)
