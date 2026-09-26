from sqlalchemy import String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import DataRuleLogicalType
from backend.common.model.base import Base
from backend.common.model.types import id_key, rel_key

__all__ = [
    'SysRoleDataRule',
    'SysRoleDept',
    'SysRoleMenu',
    'SysUserRole',
]


class SysUserRole(Base):
    """用户与角色关联表."""

    __tablename__ = 'sys_user_role'
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id'),
        {'schema': 'tenant', 'comment': '用户与角色关联表'},
    )

    id: Mapped[id_key]
    user_id: Mapped[rel_key] = mapped_column(comment='用户 ID')
    role_id: Mapped[rel_key] = mapped_column(comment='角色 ID')


class SysRoleMenu(Base):
    """角色与菜单关联表."""

    __tablename__ = 'sys_role_menu'
    __table_args__ = (
        UniqueConstraint('role_id', 'menu_id'),
        {'schema': 'tenant', 'comment': '角色与菜单关联表'},
    )

    id: Mapped[id_key]
    role_id: Mapped[rel_key] = mapped_column(comment='角色 ID')
    menu_id: Mapped[rel_key] = mapped_column(comment='菜单 ID')


class SysRoleDept(Base):
    """角色与部门数据权限关联表."""

    __tablename__ = 'sys_role_dept'
    __table_args__ = (
        UniqueConstraint('role_id', 'dept_id'),
        {'schema': 'tenant', 'comment': '角色与部门数据权限关联表'},
    )

    id: Mapped[id_key]
    role_id: Mapped[rel_key] = mapped_column(comment='角色 ID')
    dept_id: Mapped[rel_key] = mapped_column(comment='部门 ID')


class SysRoleDataRule(Base):
    """角色与数据规则关联表."""

    __tablename__ = 'sys_role_data_rule'
    __table_args__ = (
        UniqueConstraint('role_id', 'rule_id'),
        {'schema': 'tenant', 'comment': '角色与数据规则关联表'},
    )

    id: Mapped[id_key]
    role_id: Mapped[rel_key] = mapped_column(comment='角色 ID')
    rule_id: Mapped[rel_key] = mapped_column(comment='规则 ID')
    logic_op: Mapped[str] = mapped_column(
        String(8),
        default=DataRuleLogicalType.AND,
        server_default=text("'and'"),
        comment='合并逻辑 (and/or)',
    )
