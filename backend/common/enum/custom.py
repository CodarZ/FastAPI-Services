from backend.common.enum.base import IntEnum, StrEnum

__all__ = [
    'AudienceType',
    'DataScopeType',
    'LogStatusType',
    'MenuType',
    'OutboxStatusType',
    'RoleType',
    'StatusType',
    'TenantStatusType',
    'TokenType',
    'UserType',
]


class StatusType(IntEnum):
    """通用启停状态."""

    DISABLE = 0  # 停用 / 禁用
    ENABLE = 1  # 启用 / 正常


class TenantStatusType(IntEnum):
    """多租户沙箱生命周期状态."""

    PENDING = 0  # 待初始化 (Schema 已创建但未套用基线迁移)
    NORMAL = 1  # 正常活跃
    FROZEN = 2  # 冻结锁定 (欠费、违约或违规，拒绝租户域所有写请求)
    EXPIRED = 3  # 已到期 (租期结束或 License 过期)


class UserType(IntEnum):
    """用户身份类别."""

    SUPERUSER = 1  # 超级管理员 (SaaS 下为平台超管；私有化下为系统总超管)
    ADMIN = 2  # 主管理员 (SaaS 下为租户主账号；私有化下为企业主管理员)
    MEMBER = 3  # 普通成员 (SaaS 下为租户员工；私有化下为企业内部员工)


class MenuType(IntEnum):
    """菜单/权限节点类型 (RBAC 路由与按钮权限树)."""

    DIRECTORY = 0  # 目录
    MENU = 1  # 菜单
    BUTTON = 2  # 按钮 / API 权限点
    EMBEDDED = 3  # 内嵌 Iframe 组件
    LINK = 4  # 外部链接


class DataScopeType(IntEnum):
    """行级数据权限范围."""

    ALL = 1  # 全部数据权限
    CUSTOM = 2  # 自定义部门权限
    DEPT = 3  # 本部门数据权限
    DEPT_AND_CHILD = 4  # 本部门及以下数据权限
    SELF = 5  # 仅本人数据权限


class RoleType(IntEnum):
    """角色类别."""

    SYSTEM = 1  # 内置系统角色 (只读防误删)
    CUSTOM = 2  # 自定义业务角色


class OutboxStatusType(IntEnum):
    """本地事务 Outbox 事件状态."""

    PENDING = 0  # 待投递
    PROCESSING = 1  # 处理中 (已被 Worker 加锁消费，防重抢占)
    SUCCESS = 2  # 投递成功
    FAILED = 3  # 投递失败 (重试耗尽)


class LogStatusType(IntEnum):
    """日志状态."""

    FAIL = 0  # 失败
    SUCCESS = 1  # 成功


class AudienceType(StrEnum):
    """双 JWT 隔离标识."""

    ADMIN = 'fs:admin'  # 运营管理端通道 (/admin/*)
    CLIENT = 'fs:client'  # 用户自服务客户端通道 (/client/*)


class TokenType(StrEnum):
    """Token 类别标识."""

    ACCESS = 'access_token'  # 访问令牌
    REFRESH = 'refresh_token'  # 刷新令牌
