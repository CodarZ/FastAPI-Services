from backend.common.enum.base import IntEnum, StrEnum

__all__ = [
    'AudienceType',
    'DataRuleExpressionType',
    'DataRuleLogicalType',
    'DataScopeType',
    'LogStatusType',
    'MenuType',
    'OperBusinessType',
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
    """菜单权限节点类型."""

    DIRECTORY = 0  # 目录
    MENU = 1  # 菜单
    BUTTON = 2  # 按钮 / API
    EMBEDDED = 3  # 内嵌外链
    LINK = 4  # 外部链接


class DataScopeType(IntEnum):
    """行级数据权限范围."""

    ALL = 1  # 全部数据
    DEPT = 2  # 本部门数据
    DEPT_AND_CHILD = 3  # 本部门及以下数据
    SELF = 4  # 仅本人数据
    CUSTOM_DEPT = 5  # 自定义部门数据
    CUSTOM_RULE = 6  # 自定义规则数据


class DataRuleExpressionType(StrEnum):
    """数据规则条件运算操作符."""

    EQ = 'eq'  # 等于 (=)
    NE = 'ne'  # 不等于 (!=)
    GT = 'gt'  # 大于 (>)
    GTE = 'gte'  # 大于等于 (>=)
    LT = 'lt'  # 小于 (<)
    LTE = 'lte'  # 小于等于 (<=)
    LIKE = 'like'  # 模糊匹配 (LIKE)
    IN = 'in'  # 包含于 (IN)
    NOT_IN = 'not_in'  # 不包含于 (NOT IN)
    IS_NULL = 'is_null'  # 判定为空 (IS NULL)
    IS_NOT_NULL = 'is_not_null'  # 判定非空 (IS NOT NULL)


class DataRuleLogicalType(StrEnum):
    """数据规则多条件合并逻辑符."""

    AND = 'and'  # 且: 必须同时满足
    OR = 'or'  # 或: 满足其一即可


class RoleType(IntEnum):
    """角色类别."""

    SYSTEM = 1  # 内置系统角色 (只读防误删)
    CUSTOM = 2  # 自定义业务角色


class OutboxStatusType(IntEnum):
    """本地事务 Outbox 事件状态."""

    PENDING = 0  # 待投递
    PROCESSING = 1  # 处理中
    SUCCESS = 2  # 投递成功
    FAILED = 3  # 投递失败


class LogStatusType(IntEnum):
    """日志执行状态."""

    FAIL = 0  # 失败
    SUCCESS = 1  # 成功


class OperBusinessType(IntEnum):
    """操作审计业务类型."""

    OTHER = 0  # 其它
    INSERT = 1  # 新增
    UPDATE = 2  # 修改
    DELETE = 3  # 删除
    VIEW = 4  # 查看敏感数据
    EXPORT = 5  # 导出
    IMPORT = 6  # 导入
    GRANT = 7  # 授权
    FORCE = 8  # 强退


class AudienceType(StrEnum):
    """双 JWT 隔离标识."""

    ADMIN = 'fs:admin'  # 运营管理端通道 (/admin/*)
    CLIENT = 'fs:client'  # 用户自服务客户端通道 (/client/*)


class TokenType(StrEnum):
    """Token 类别标识."""

    ACCESS = 'access_token'  # 访问令牌
    REFRESH = 'refresh_token'  # 刷新令牌
