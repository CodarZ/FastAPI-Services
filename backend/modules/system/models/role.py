from functools import partial

from sqlalchemy import Integer, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import DataScopeType, RoleType, StatusType
from backend.common.model.base import Base
from backend.common.model.mixins import AuditMixin, DateTimeMixin
from backend.common.model.types import id_key, uid_key
from backend.utils.uid import gen_uid

__all__ = ['SysRole']


class SysRole(Base, DateTimeMixin, AuditMixin):
    """系统角色表."""

    __tablename__ = 'sys_role'
    __table_args__ = {'schema': 'tenant', 'comment': '系统角色表'}

    id: Mapped[id_key]
    uid: Mapped[uid_key] = mapped_column(insert_default=partial(gen_uid, 'rol'))

    name: Mapped[str] = mapped_column(String(64), comment='角色名称')
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment='角色编码')
    role_type: Mapped[int] = mapped_column(
        SmallInteger,
        default=RoleType.CUSTOM,
        server_default=text(str(RoleType.CUSTOM.value)),
        comment='角色类型 (1=系统内置 2=自定义)',
    )

    data_scope: Mapped[int] = mapped_column(
        SmallInteger,
        default=DataScopeType.SELF,
        server_default=text(str(DataScopeType.SELF.value)),
        comment='数据范围 (1=全部 2=本部门 3=本部门及下级 4=本人 5=自定义部门 6=自定义规则)',
    )
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'), comment='排序')
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=StatusType.ENABLE,
        server_default=text(str(StatusType.ENABLE.value)),
        comment='角色状态 (0=停用 1=正常)',
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment='备注')
